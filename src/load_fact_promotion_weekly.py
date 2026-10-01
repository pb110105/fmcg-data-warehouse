import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import load_dimension


COLUMNS = [
    "product_key",
    "store_key",
    "week_key",
    "has_display",
    "has_mailer",
    "display_location_codes",
    "mailer_location_codes",
    "source_row_count",
    "promotion_code_unknown_flag",
    "scope_rule_version",
    "etl_batch_id",
]


def load_promotions(conn, run_id, scope_dir, raw_dir):
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

        # Với bộ nguồn hiện tại, mọi mã trong promotions phải có
        # trong CSV phân loại. Không âm thầm bỏ mã chưa phân loại.
        missing_scope = conn.execute(
            """
            SELECT COUNT(*)
            FROM q_promotions p
            WHERE NOT EXISTS (
                SELECT 1 FROM input_scope_check c
                WHERE c.product_id = p.product_id
            )
            """
        ).fetchone()[0]

        require(
            missing_scope == 0,
            f"Có {missing_scope:,} dòng promotions chưa có phân loại.",
        )

        conn.execute(
            """
            CREATE TEMP VIEW promotion_in_scope AS
            SELECT p.*
            FROM q_promotions p
            JOIN input_scope_check c USING (product_id)
            WHERE c.scope_status = 'IN_SCOPE'
            """
        )

        source_count = conn.execute(
            "SELECT COUNT(*) FROM promotion_in_scope"
        ).fetchone()[0]

        require(source_count > 0, "Không có promotions IN_SCOPE.")

        print(
            f"SOURCE | Promotions IN_SCOPE | {source_count:,} dòng",
            flush=True,
        )
        print("Đang tổng hợp sản phẩm–cửa hàng–tuần...", flush=True)

        # Không DISTINCT toàn bộ nguồn trước khi COUNT:
        # source_row_count phải phản ánh đủ các dòng được tổng hợp.
        conn.execute(
            """
            CREATE TEMP TABLE promotion_grouped ON COMMIT DROP AS
            SELECT
                product_id,
                store_id,
                week,

                CASE
                    WHEN BOOL_OR(
                        display_location IN
                        ('1','2','3','4','5','6','7','9')
                    ) THEN TRUE
                    WHEN BOOL_OR(
                        display_location IS NULL
                        OR display_location NOT IN
                        ('0','A','1','2','3','4','5','6','7','9')
                    ) THEN NULL::boolean
                    ELSE FALSE
                END AS has_display,

                CASE
                    WHEN BOOL_OR(
                        mailer_location IN
                        ('A','C','D','F','H','J','L','P','X','Z')
                    ) THEN TRUE
                    WHEN BOOL_OR(
                        mailer_location IS NULL
                        OR mailer_location NOT IN
                        ('0','A','C','D','F','H','J','L','P','X','Z')
                    ) THEN NULL::boolean
                    ELSE FALSE
                END AS has_mailer,

                ARRAY_AGG(
                    DISTINCT display_location
                    ORDER BY display_location
                ) AS display_location_codes,

                ARRAY_AGG(
                    DISTINCT mailer_location
                    ORDER BY mailer_location
                ) AS mailer_location_codes,

                COUNT(*) AS source_row_count,

                BOOL_OR(
                    display_location IS NULL
                    OR display_location NOT IN
                    ('0','A','1','2','3','4','5','6','7','9')
                    OR mailer_location IS NULL
                    OR mailer_location NOT IN
                    ('0','A','C','D','F','H','J','L','P','X','Z')
                ) AS promotion_code_unknown_flag

            FROM promotion_in_scope
            GROUP BY product_id, store_id, week
            """
        )

        conn.execute(
            """
            ALTER TABLE promotion_grouped
            ADD PRIMARY KEY (product_id, store_id, week)
            """
        )
        conn.execute("ANALYZE promotion_grouped")

        grouped_count, represented_rows = conn.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(source_row_count), 0)
            FROM promotion_grouped
            """
        ).fetchone()

        require(
            represented_rows == source_count,
            "Tổng source_row_count không khớp số dòng nguồn.",
        )

        bad_products = conn.execute(
            """
            SELECT COUNT(*)
            FROM promotion_grouped g
            LEFT JOIN dw.dim_product p USING (product_id)
            WHERE p.product_key IS NULL
               OR p.scope_status <> 'IN_SCOPE'
               OR p.source_lookup_missing_flag
               OR p.scope_rule_version <> %s
               OR p.etl_batch_id <> %s
            """,
            (metadata["scope_rule_version"], batch_id),
        ).fetchone()[0]

        require(
            bad_products == 0,
            f"Có {bad_products:,} nhóm không khớp Dim_Product.",
        )

        conn.execute(
            """
            CREATE TEMP TABLE expected_promotion ON COMMIT DROP AS
            SELECT
                p.product_key,
                s.store_key,
                w.week_key,
                g.has_display,
                g.has_mailer,
                g.display_location_codes,
                g.mailer_location_codes,
                g.source_row_count,
                g.promotion_code_unknown_flag,
                %s::text AS scope_rule_version,
                %s::bigint AS etl_batch_id
            FROM promotion_grouped g
            LEFT JOIN dw.dim_product p
              ON p.product_id = g.product_id
            LEFT JOIN dw.dim_store s
              ON s.store_id = g.store_id
             AND s.etl_batch_id = %s
            LEFT JOIN dw.dim_week w
              ON w.source_calendar_id = %s
             AND w.source_week = g.week
            """,
            (
                metadata["scope_rule_version"],
                batch_id,
                batch_id,
                metadata["source_calendar_id"],
            ),
        )

        mapped_count, missing_keys = conn.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (
                       WHERE product_key IS NULL
                          OR store_key IS NULL
                          OR week_key IS NULL
                   )
            FROM expected_promotion
            """
        ).fetchone()

        require(
            mapped_count == grouped_count and missing_keys == 0,
            "Ánh xạ Dimension làm thay đổi số nhóm hoặc thiếu khóa.",
        )

        conn.execute(
            """
            ALTER TABLE expected_promotion
            ADD PRIMARY KEY (product_key, store_key, week_key)
            """
        )
        conn.execute("ANALYZE expected_promotion")

        print(
            f"GROUPED | {grouped_count:,} nhóm | Đang nạp và đối soát...",
            flush=True,
        )

        result = load_dimension(
            conn, batch_id, run_id,
            "fact_promotion_weekly", "expected_promotion",
            ("product_key", "store_key", "week_key"),
            COLUMNS,
        )

        target_rows = conn.execute(
            """
            SELECT COALESCE(SUM(source_row_count), 0)
            FROM dw.fact_promotion_weekly
            """
        ).fetchone()[0]

        require(
            target_rows == source_count,
            "Fact không bảo toàn số dòng nguồn được tổng hợp.",
        )

        multiple, unknown, null_display, null_mailer = conn.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE multiple_source_rows_flag),
                COUNT(*) FILTER (WHERE promotion_code_unknown_flag),
                COUNT(*) FILTER (WHERE has_display IS NULL),
                COUNT(*) FILTER (WHERE has_mailer IS NULL)
            FROM dw.fact_promotion_weekly
            """
        ).fetchone()

        details = {
            "source_in_scope_rows": source_count,
            "product_store_week_groups": grouped_count,
            "rows_consolidated": source_count - grouped_count,
            "multiple_source_row_groups": multiple,
            "unknown_code_groups": unknown,
            "null_display_groups": null_display,
            "null_mailer_groups": null_mailer,
            "source_calendar_id": metadata["source_calendar_id"],
        }

        conn.execute(
            """
            INSERT INTO audit.reconciliation_result (
                etl_batch_id, dw_load_id,
                source_name, target_name, metric_name,
                source_value, target_value, status, details
            )
            VALUES (
                %s, %s, 'staging.promotions IN_SCOPE',
                'dw.fact_promotion_weekly',
                'source_rows_vs_sum_source_row_count',
                %s, %s, 'PASS', %s
            )
            """,
            (
                batch_id, run_id,
                source_count, target_rows, Jsonb(details),
            ),
        )

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.fact_promotion_weekly',
                'PROMOTION_UNKNOWN_CODES_V1',
                'WARNING', %s, %s, %s
            )
            """,
            (
                batch_id, run_id,
                "FAIL" if unknown else "PASS",
                unknown, Jsonb(details),
            ),
        )

    table, total, inserted, unchanged = result
    print(f"\nPASS | {table} | {total:,} dòng")
    print(f"INSERT | {inserted:,} dòng mới")
    print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
    print("PASS | Đối chiếu hai chiều | 0 khác biệt")
    print(f"PASS | Tổng source_row_count | {target_rows:,}")
    print(f"INFO | Nhóm có nhiều dòng nguồn | {multiple:,}")
    print(f"INFO | Nhóm có mã chưa biết | {unknown:,}")
    print(f"INFO | has_display NULL | {null_display:,}")
    print(f"INFO | has_mailer NULL | {null_mailer:,}")
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
            load_promotions(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_fact_promotion_weekly",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()