import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import load_dimension


CAMPAIGN_COLUMNS = [
    "campaign_id",
    "campaign_type",
    "start_date",
    "end_date",
    "etl_batch_id",
]

COUPON_COLUMNS = [
    "campaign_key",
    "campaign_id",
    "coupon_upc",
    "etl_batch_id",
]


def assert_zero(conn, query, message):
    count = conn.execute(query).fetchone()[0]
    require(count == 0, f"{message}: {count:,}")
    return count


def load_campaign_coupon(conn, run_id, scope_dir, raw_dir):
    with conn.transaction():
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )

        run = conn.execute(
            """
            SELECT source_batch_id, pipeline_version,
                   scope_rule_version, scope_file_sha256,
                   source_calendar_id, status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            FOR UPDATE
            """,
            (run_id,),
        ).fetchone()

        require(
            run is not None and run[5] == "RUNNING",
            "DW load phải tồn tại và đang RUNNING.",
        )
        batch_id = run[0]

        metadata = check_inputs(
            conn, batch_id, scope_dir, raw_dir
        )

        require(
            tuple(run[1:5]) == (
                PIPELINE_VERSION,
                metadata["scope_rule_version"],
                metadata["scope_file_sha256"],
                metadata["source_calendar_id"],
            ),
            "Đầu vào không khớp nhật ký DW.",
        )

        dq = conn.execute(
            """
            WITH latest AS (
                SELECT MAX(checked_at) AS checked_at
                FROM audit.data_quality_result
                WHERE dw_load_id = %s
                  AND etl_batch_id = %s
                  AND LEFT(rule_code, 6) = 'DQ_V1_'
            )
            SELECT COUNT(*),
                   COUNT(DISTINCT rule_code),
                   COUNT(*) FILTER (
                       WHERE severity = 'ERROR'
                         AND status = 'FAIL'
                   )
            FROM audit.data_quality_result
            WHERE dw_load_id = %s
              AND etl_batch_id = %s
              AND LEFT(rule_code, 6) = 'DQ_V1_'
              AND checked_at = (SELECT checked_at FROM latest)
            """,
            (run_id, batch_id, run_id, batch_id),
        ).fetchone()

        require(
            dq == (57, 57, 0),
            f"Chưa đạt kiểm tra chất lượng đầu vào: {dq}",
        )

        create_normalized_views(conn, batch_id)

        conn.execute(
            """
            CREATE TEMP TABLE expected_campaign ON COMMIT DROP AS
            SELECT DISTINCT
                   campaign_id,
                   campaign_type,
                   start_date,
                   end_date,
                   %s::bigint AS etl_batch_id
            FROM q_campaign_descriptions
            """,
            (batch_id,),
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM expected_campaign
            WHERE campaign_id IS NULL
               OR BTRIM(campaign_id) = ''
               OR campaign_type IS NULL
               OR BTRIM(campaign_type) = ''
               OR start_date IS NULL
               OR end_date IS NULL
               OR NOT isfinite(start_date)
               OR NOT isfinite(end_date)
               OR start_date > end_date
            """,
            "Chiến dịch có mã, loại hoặc ngày không hợp lệ",
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM (
                SELECT campaign_id
                FROM expected_campaign
                GROUP BY campaign_id
                HAVING COUNT(*) > 1
            ) x
            """,
            "Mã chiến dịch có thuộc tính mâu thuẫn",
        )

        conn.execute(
            """
            ALTER TABLE expected_campaign
            ADD PRIMARY KEY (campaign_id)
            """
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM expected_campaign c
            WHERE NOT EXISTS (
                SELECT 1 FROM dw.dim_date d
                WHERE d.full_date = c.start_date
            )
            OR NOT EXISTS (
                SELECT 1 FROM dw.dim_date d
                WHERE d.full_date = c.end_date
            )
            """,
            "Ngày chiến dịch chưa được Dim_Date bao phủ",
        )

        # Mọi chiến dịch xuất hiện trong nghiệp vụ phải có mô tả.
        assert_zero(
            conn,
            """
            WITH campaign_ids AS (
                SELECT campaign_id FROM q_campaigns
                UNION
                SELECT campaign_id FROM q_coupons
                UNION
                SELECT campaign_id FROM q_coupon_redemptions
            )
            SELECT COUNT(*)
            FROM campaign_ids i
            WHERE NOT EXISTS (
                SELECT 1 FROM expected_campaign c
                WHERE c.campaign_id = i.campaign_id
            )
            """,
            "Chiến dịch nghiệp vụ thiếu mô tả",
        )

        # Một coupon có thể áp dụng cho nhiều sản phẩm.
        # Dim_Coupon chỉ giữ một dòng cho mỗi cặp chiến dịch–coupon.
        conn.execute(
            """
            CREATE TEMP TABLE coupon_pairs ON COMMIT DROP AS
            SELECT DISTINCT campaign_id, coupon_upc
            FROM q_coupons
            """
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM coupon_pairs
            WHERE campaign_id IS NULL
               OR BTRIM(campaign_id) = ''
               OR coupon_upc IS NULL
               OR BTRIM(coupon_upc) = ''
            """,
            "Coupon có khóa NULL hoặc rỗng",
        )

        conn.execute(
            """
            ALTER TABLE coupon_pairs
            ADD PRIMARY KEY (campaign_id, coupon_upc)
            """
        )

        # Không tự tạo coupon từ redemption thiếu liên kết nguồn.
        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM q_coupon_redemptions r
            WHERE NOT EXISTS (
                SELECT 1 FROM coupon_pairs c
                WHERE c.campaign_id = r.campaign_id
                  AND c.coupon_upc = r.coupon_upc
            )
            """,
            "Sử dụng coupon không khớp cặp chiến dịch–coupon",
        )

        campaign_result = load_dimension(
            conn, batch_id, run_id,
            "dim_campaign", "expected_campaign",
            "campaign_id", CAMPAIGN_COLUMNS,
        )

        # Tra campaign_key sau khi Dim_Campaign đã được nạp.
        conn.execute(
            """
            CREATE TEMP TABLE expected_coupon ON COMMIT DROP AS
            SELECT
                d.campaign_key,
                c.campaign_id,
                c.coupon_upc,
                %s::bigint AS etl_batch_id
            FROM coupon_pairs c
            LEFT JOIN dw.dim_campaign d
              ON d.campaign_id = c.campaign_id
            """,
            (batch_id,),
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM expected_coupon
            WHERE campaign_key IS NULL
            """,
            "Coupon không tra được campaign_key",
        )

        conn.execute(
            """
            ALTER TABLE expected_coupon
            ADD PRIMARY KEY (campaign_id, coupon_upc)
            """
        )

        coupon_result = load_dimension(
            conn, batch_id, run_id,
            "dim_coupon", "expected_coupon",
            ("campaign_id", "coupon_upc"),
            COUPON_COLUMNS,
        )

        assert_zero(
            conn,
            """
            SELECT COUNT(*)
            FROM dw.dim_coupon c
            LEFT JOIN dw.dim_campaign d
              ON d.campaign_key = c.campaign_key
             AND d.campaign_id = c.campaign_id
            WHERE d.campaign_key IS NULL
            """,
            "Dim_Coupon liên kết sai Dim_Campaign",
        )

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.dim_campaign + dw.dim_coupon',
                'CAMPAIGN_COUPON_LINKS_V1',
                'INFO', 'PASS', 0, %s
            )
            """,
            (
                batch_id, run_id,
                Jsonb({
                    "campaign_dates_valid": True,
                    "campaign_dates_in_dim_date": True,
                    "source_campaign_links_valid": True,
                    "redemption_coupon_pairs_valid": True,
                    "coupon_campaign_keys_valid": True,
                    "coupon_business_key": [
                        "campaign_id", "coupon_upc"
                    ],
                }),
            ),
        )

    # Chỉ báo thành công sau khi cả hai bảng đã commit.
    for table, total, inserted, unchanged in (
        campaign_result, coupon_result
    ):
        print(f"PASS | {table} | {total:,} dòng")
        print(f"INSERT | {inserted:,} dòng mới")
        print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
        print("PASS | Đối chiếu hai chiều | 0 khác biệt")

    print("PASS | Ngày chiến dịch và liên kết chiến dịch–coupon")
    print(f"dw_load_id={run_id} vẫn RUNNING.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dw-load-id", type=int, required=True)
    parser.add_argument(
        "--scope-dir",
        type=Path,
        default=ROOT / "data/landing/fmcg_classification_v1_3",
    )
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/raw/complete_journey",
    )
    args = parser.parse_args()

    with connect_db() as conn:
        acquire_lock(conn)

        state = conn.execute(
            "SELECT status FROM audit.dw_load WHERE dw_load_id = %s",
            (args.dw_load_id,),
        ).fetchone()

        require(
            state is not None and state[0] == "RUNNING",
            "DW load phải tồn tại và đang RUNNING.",
        )

        try:
            load_campaign_coupon(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_dim_campaign_coupon",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()