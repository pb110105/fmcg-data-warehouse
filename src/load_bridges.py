import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import load_dimension


def prepare_bridge(
    conn, batch_id, name, source_table, source_columns,
    mapping_query, target_keys,
):
    # Các tên bảng/cột do chương trình quy định.
    links_table = f"links_{name}"
    expected_table = f"expected_{name}"
    source_column_list = ", ".join(source_columns)

    raw_count = conn.execute(
        f"SELECT COUNT(*) FROM {source_table}"
    ).fetchone()[0]

    conn.execute(
        f"""
        CREATE TEMP TABLE {links_table} ON COMMIT DROP AS
        SELECT DISTINCT {source_column_list}
        FROM {source_table}
        """
    )

    invalid_condition = " OR ".join(
        f"{column} IS NULL OR BTRIM({column}) = ''"
        for column in source_columns
    )

    invalid = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {links_table}
        WHERE {invalid_condition}
        """
    ).fetchone()[0]

    require(invalid == 0, f"{name}: có khóa nguồn NULL hoặc rỗng.")

    conn.execute(
        f"""
        ALTER TABLE {links_table}
        ADD PRIMARY KEY ({source_column_list})
        """
    )

    distinct_count = conn.execute(
        f"SELECT COUNT(*) FROM {links_table}"
    ).fetchone()[0]

    conn.execute(
        f"""
        CREATE TEMP TABLE {expected_table} ON COMMIT DROP AS
        {mapping_query}
        """,
        (batch_id,),
    )

    missing_condition = " OR ".join(
        f"{column} IS NULL" for column in target_keys
    )

    missing = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {expected_table}
        WHERE {missing_condition}
        """
    ).fetchone()[0]

    require(
        missing == 0,
        f"{name}: có {missing:,} liên kết không tra được khóa Dimension.",
    )

    mapped_count = conn.execute(
        f"SELECT COUNT(*) FROM {expected_table}"
    ).fetchone()[0]

    require(
        mapped_count == distinct_count,
        f"{name}: phép nối Dimension làm thay đổi số liên kết.",
    )

    # Bắt cả trường hợp nhiều liên kết nguồn ánh xạ vào cùng khóa đích.
    conn.execute(
        f"""
        ALTER TABLE {expected_table}
        ADD PRIMARY KEY ({", ".join(target_keys)})
        """
    )

    return {
        "source_table": source_table,
        "expected_table": expected_table,
        "source_rows": raw_count,
        "distinct_links": distinct_count,
        "duplicate_rows_removed": raw_count - distinct_count,
    }


def write_bridge_audit(conn, batch_id, run_id, table, stats):
    removed = stats["duplicate_rows_removed"]

    conn.execute(
        """
        INSERT INTO audit.data_quality_result (
            etl_batch_id, dw_load_id, table_name,
            rule_code, severity, status, affected_rows, details
        )
        VALUES (%s, %s, %s, %s, 'INFO', 'PASS', %s, %s)
        """,
        (
            batch_id,
            run_id,
            f"dw.{table}",
            f"{table.upper()}_DEDUP_V1",
            removed,
            Jsonb({
                **stats,
                "action": "Giữ một dòng cho mỗi liên kết phân biệt",
                "count_unit": "excess_source_rows_removed",
                "source_preserved_in_staging": True,
            }),
        ),
    )

    # Số dòng nguồn = liên kết giữ lại + dòng trùng dư.
    conn.execute(
        """
        INSERT INTO audit.reconciliation_result (
            etl_batch_id, dw_load_id,
            source_name, target_name, metric_name,
            source_value, target_value, status, details
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'PASS', %s)
        """,
        (
            batch_id,
            run_id,
            stats["source_table"],
            f"dw.{table}",
            "source_rows_equals_distinct_plus_duplicates",
            stats["source_rows"],
            stats["distinct_links"] + removed,
            Jsonb(stats),
        ),
    )


def load_bridges(conn, run_id, scope_dir, raw_dir):
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

        # Mốc của check_dw_quality.py phiên bản hiện tại.
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

        campaign_stats = prepare_bridge(
            conn,
            batch_id,
            "campaign_household",
            "q_campaigns",
            ["campaign_id", "household_id"],
            """
            SELECT
                c.campaign_key,
                h.household_key,
                %s::bigint AS etl_batch_id
            FROM links_campaign_household s
            LEFT JOIN dw.dim_campaign c
              ON c.campaign_id = s.campaign_id
            LEFT JOIN dw.dim_household h
              ON h.household_id = s.household_id
            """,
            ["campaign_key", "household_key"],
        )

        coupon_stats = prepare_bridge(
            conn,
            batch_id,
            "coupon_product",
            "q_coupons",
            ["campaign_id", "coupon_upc", "product_id"],
            """
            SELECT
                c.coupon_key,
                p.product_key,
                %s::bigint AS etl_batch_id
            FROM links_coupon_product s
            LEFT JOIN dw.dim_coupon c
              ON c.campaign_id = s.campaign_id
             AND c.coupon_upc = s.coupon_upc
            LEFT JOIN dw.dim_product p
              ON p.product_id = s.product_id
            """,
            ["coupon_key", "product_key"],
        )

        campaign_result = load_dimension(
            conn, batch_id, run_id,
            "bridge_campaign_household",
            campaign_stats["expected_table"],
            ("campaign_key", "household_key"),
            ["campaign_key", "household_key", "etl_batch_id"],
        )

        coupon_result = load_dimension(
            conn, batch_id, run_id,
            "bridge_coupon_product",
            coupon_stats["expected_table"],
            ("coupon_key", "product_key"),
            ["coupon_key", "product_key", "etl_batch_id"],
        )

        write_bridge_audit(
            conn, batch_id, run_id,
            "bridge_campaign_household", campaign_stats,
        )
        write_bridge_audit(
            conn, batch_id, run_id,
            "bridge_coupon_product", coupon_stats,
        )

    # In kết quả sau khi cả hai Bridge và audit đã commit.
    for result, stats in (
        (campaign_result, campaign_stats),
        (coupon_result, coupon_stats),
    ):
        table, total, inserted, unchanged = result
        print(f"\nPASS | {table} | {total:,} liên kết")
        print(f"SOURCE | {stats['source_rows']:,} dòng")
        print(f"DISTINCT | {stats['distinct_links']:,} liên kết")
        print(
            f"DEDUP | {stats['duplicate_rows_removed']:,} dòng trùng dư"
        )
        print(f"INSERT | {inserted:,} dòng mới")
        print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
        print("PASS | Đối chiếu hai chiều | 0 khác biệt")

    print(f"\ndw_load_id={run_id} vẫn RUNNING.")


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
            load_bridges(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_bridges",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()