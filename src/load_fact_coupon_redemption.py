import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import load_dimension


KEYS = (
    "household_key",
    "coupon_key",
    "campaign_key",
    "redemption_date_key",
)

COLUMNS = [
    *KEYS,
    "redemption_record_count",
    "etl_batch_id",
]


def load_redemptions(conn, run_id, scope_dir, raw_dir):
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

        source_count = conn.execute(
            "SELECT COUNT(*) FROM q_coupon_redemptions"
        ).fetchone()[0]

        require(
            source_count == 2102,
            f"Số dòng nguồn khác mốc hiện tại: {source_count:,}",
        )

        invalid = conn.execute(
            """
            SELECT COUNT(*)
            FROM q_coupon_redemptions
            WHERE household_id IS NULL
               OR BTRIM(household_id) = ''
               OR campaign_id IS NULL
               OR BTRIM(campaign_id) = ''
               OR coupon_upc IS NULL
               OR BTRIM(coupon_upc) = ''
               OR redemption_date IS NULL
               OR NOT isfinite(redemption_date)
            """
        ).fetchone()[0]

        require(invalid == 0, "Nguồn có khóa hoặc ngày không hợp lệ.")

        # Không DISTINCT: trùng grain phải được phát hiện, không tự xóa.
        duplicate_groups = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT household_id, campaign_id,
                       coupon_upc, redemption_date
                FROM q_coupon_redemptions
                GROUP BY household_id, campaign_id,
                         coupon_upc, redemption_date
                HAVING COUNT(*) > 1
            ) x
            """
        ).fetchone()[0]

        require(
            duplicate_groups == 0,
            f"Có {duplicate_groups:,} nhóm trùng grain redemption.",
        )

        # Tra coupon bằng cả campaign_id và coupon_upc.
        # Không nối với Bridge_Coupon_Product để tránh nhân dòng.
        conn.execute(
            """
            CREATE TEMP TABLE mapped_redemption ON COMMIT DROP AS
            SELECT
                h.household_key,
                c.coupon_key,
                g.campaign_key,
                d.date_key AS redemption_date_key,
                1::smallint AS redemption_record_count,
                %s::bigint AS etl_batch_id,
                r.redemption_date,
                g.start_date,
                g.end_date,
                c.campaign_key AS coupon_campaign_key
            FROM q_coupon_redemptions r
            LEFT JOIN dw.dim_household h
              ON h.household_id = r.household_id
             AND h.etl_batch_id = %s
            LEFT JOIN dw.dim_campaign g
              ON g.campaign_id = r.campaign_id
             AND g.etl_batch_id = %s
            LEFT JOIN dw.dim_coupon c
              ON c.campaign_id = r.campaign_id
             AND c.coupon_upc = r.coupon_upc
             AND c.etl_batch_id = %s
            LEFT JOIN dw.dim_date d
              ON d.full_date = r.redemption_date
            """,
            (batch_id, batch_id, batch_id, batch_id),
        )

        mapped_count, invalid_mapping = conn.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (
                       WHERE household_key IS NULL
                          OR coupon_key IS NULL
                          OR campaign_key IS NULL
                          OR redemption_date_key IS NULL
                          OR coupon_campaign_key
                             IS DISTINCT FROM campaign_key
                          OR start_date IS NULL
                          OR end_date IS NULL
                          OR redemption_date NOT BETWEEN
                             start_date AND end_date
                   )
            FROM mapped_redemption
            """
        ).fetchone()

        require(
            mapped_count == source_count,
            "Phép nối Dimension làm thay đổi số dòng.",
        )
        require(
            invalid_mapping == 0,
            f"Có {invalid_mapping:,} dòng sai khóa hoặc ngày chiến dịch.",
        )

        missing_assignment = conn.execute(
            """
            SELECT COUNT(*)
            FROM mapped_redemption r
            WHERE NOT EXISTS (
                SELECT 1
                FROM dw.bridge_campaign_household b
                WHERE b.campaign_key = r.campaign_key
                  AND b.household_key = r.household_key
                  AND b.etl_batch_id = r.etl_batch_id
            )
            """
        ).fetchone()[0]

        require(
            missing_assignment == 0,
            f"Có {missing_assignment:,} dòng thiếu liên kết hộ–chiến dịch.",
        )

        columns = ", ".join(COLUMNS)

        conn.execute(
            f"""
            CREATE TEMP TABLE expected_redemption ON COMMIT DROP AS
            SELECT {columns}
            FROM mapped_redemption
            """
        )

        conn.execute(
            f"""
            ALTER TABLE expected_redemption
            ADD PRIMARY KEY ({", ".join(KEYS)})
            """
        )

        result = load_dimension(
            conn, batch_id, run_id,
            "fact_coupon_redemption", "expected_redemption",
            KEYS, COLUMNS,
        )

        record_count = conn.execute(
            """
            SELECT COALESCE(SUM(redemption_record_count), 0)
            FROM dw.fact_coupon_redemption
            """
        ).fetchone()[0]

        require(
            record_count == source_count,
            "Tổng redemption_record_count không khớp nguồn.",
        )

        households, campaigns, coupons = conn.execute(
            """
            SELECT COUNT(DISTINCT household_key),
                   COUNT(DISTINCT campaign_key),
                   COUNT(DISTINCT coupon_key)
            FROM dw.fact_coupon_redemption
            """
        ).fetchone()

        details = {
            "scope": "ALL_SOURCE",
            "source_rows": source_count,
            "mapped_rows": mapped_count,
            "invalid_mapping_rows": invalid_mapping,
            "missing_household_campaign_rows": missing_assignment,
            "distinct_households": households,
            "distinct_campaigns": campaigns,
            "distinct_campaign_coupon_pairs": coupons,
            "product_attribution": "Không suy đoán sản phẩm đã mua",
        }

        conn.execute(
            """
            INSERT INTO audit.reconciliation_result (
                etl_batch_id, dw_load_id,
                source_name, target_name, metric_name,
                source_value, target_value, status, details
            )
            VALUES (
                %s, %s, 'staging.coupon_redemptions ALL_SOURCE',
                'dw.fact_coupon_redemption',
                'sum_redemption_record_count',
                %s, %s, 'PASS', %s
            )
            """,
            (
                batch_id, run_id,
                source_count, record_count, Jsonb(details),
            ),
        )

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.fact_coupon_redemption',
                'REDEMPTION_LINKS_DATES_V1',
                'INFO', 'PASS', 0, %s
            )
            """,
            (batch_id, run_id, Jsonb(details)),
        )

    table, total, inserted, unchanged = result
    print(f"\nPASS | {table} | {total:,} dòng")
    print(f"INSERT | {inserted:,} dòng mới")
    print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
    print("PASS | Đối chiếu hai chiều | 0 khác biệt")
    print(f"PASS | Tổng redemption_record_count | {record_count:,}")
    print("PASS | Khóa, ngày và liên kết hộ–chiến dịch")
    print(f"INFO | Số hộ | {households:,}")
    print(f"INFO | Số chiến dịch | {campaigns:,}")
    print(f"INFO | Số cặp chiến dịch–coupon | {coupons:,}")
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
            load_redemptions(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_fact_coupon_redemption",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()