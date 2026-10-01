import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require, EXPECTED
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import load_dimension


MONEY = [
    "sales_value",
    "retail_disc",
    "coupon_disc",
    "coupon_match_disc",
]

MEASURES = ["quantity", *MONEY]

COLUMNS = [
    "basket_id",
    "product_key",
    "household_key",
    "store_key",
    "date_key",
    "week_key",
    "transaction_timestamp",
    "quantity",
    *MONEY,
    "scope_rule_version",
    "etl_batch_id",
]


def load_sales(conn, run_id, scope_dir, raw_dir):
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

        # Lọc theo đúng CSV đã được check_inputs kiểm tra.
        conn.execute(
            """
            CREATE TEMP VIEW sales_in_scope AS
            SELECT t.*
            FROM q_transactions t
            JOIN input_scope_check c USING (product_id)
            WHERE c.scope_status = 'IN_SCOPE'
            """
        )

        source_count = conn.execute(
            "SELECT COUNT(*) FROM sales_in_scope"
        ).fetchone()[0]

        require(
            source_count == EXPECTED["IN_SCOPE"][0],
            f"Số dòng IN_SCOPE không khớp: {source_count:,}",
        )

        # Không dùng ROUND để che giá trị sai đơn vị hoặc bất thường.
        for column in MEASURES:
            invalid = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM sales_in_scope
                WHERE {column} IS NULL
                   OR {column}::text IN (
                       'NaN', 'Infinity', '-Infinity'
                   )
                   OR {column} < 0
                """
            ).fetchone()[0]

            require(
                invalid == 0,
                f"{column}: có {invalid:,} số đo không hợp lệ.",
            )

        noise_counts = {}

        for column in MONEY:
            invalid, tiny = conn.execute(
                f"""
                SELECT
                    COUNT(*) FILTER (
                        WHERE ABS(
                            {column} * 100
                            - ROUND({column} * 100)
                        ) >= 0.000001
                    ),
                    COUNT(*) FILTER (
                        WHERE ABS(
                            {column} * 100
                            - ROUND({column} * 100)
                        ) > 0
                          AND ABS(
                            {column} * 100
                            - ROUND({column} * 100)
                        ) < 0.000001
                    )
                FROM sales_in_scope
                """
            ).fetchone()

            require(
                invalid == 0,
                f"{column}: có {invalid:,} dòng lệch cent vượt ngưỡng.",
            )
            noise_counts[column] = tiny

        # Kiểm tra Dim_Product đồng bộ phân loại và nguồn.
        bad_products = conn.execute(
            """
            SELECT COUNT(*)
            FROM sales_in_scope t
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
            f"Có {bad_products:,} giao dịch không khớp Dim_Product.",
        )

        bad_time = conn.execute(
            """
            SELECT COUNT(*)
            FROM sales_in_scope
            WHERE transaction_timestamp IS NULL
               OR NOT isfinite(transaction_timestamp)
               OR week IS NULL
            """
        ).fetchone()[0]

        require(bad_time == 0, "Có timestamp hoặc week không hợp lệ.")

        # LEFT JOIN để phát hiện thiếu khóa, không làm mất dòng âm thầm.
        conn.execute(
            """
            CREATE TEMP TABLE expected_sales ON COMMIT DROP AS
            SELECT
                t.basket_id,
                p.product_key,
                h.household_key,
                s.store_key,
                d.date_key,
                w.week_key,
                t.transaction_timestamp,
                t.quantity,
                ROUND(t.sales_value, 2) AS sales_value,
                ROUND(t.retail_disc, 2) AS retail_disc,
                ROUND(t.coupon_disc, 2) AS coupon_disc,
                ROUND(t.coupon_match_disc, 2) AS coupon_match_disc,
                %s::text AS scope_rule_version,
                %s::bigint AS etl_batch_id
            FROM sales_in_scope t
            LEFT JOIN dw.dim_product p
              ON p.product_id = t.product_id
            LEFT JOIN dw.dim_household h
              ON h.household_id = t.household_id
             AND h.etl_batch_id = %s
            LEFT JOIN dw.dim_store s
              ON s.store_id = t.store_id
             AND s.etl_batch_id = %s
            LEFT JOIN dw.dim_date d
              ON d.full_date = (
                  t.transaction_timestamp
                  AT TIME ZONE 'America/New_York'
              )::date
            LEFT JOIN dw.dim_week w
              ON w.source_calendar_id = %s
             AND w.source_week = t.week
             AND d.full_date BETWEEN
                 w.coverage_start_date AND w.coverage_end_date
            """,
            (
                metadata["scope_rule_version"],
                batch_id,
                batch_id,
                batch_id,
                metadata["source_calendar_id"],
            ),
        )

        mapped_count, missing = conn.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (
                       WHERE basket_id IS NULL
                          OR BTRIM(basket_id) = ''
                          OR product_key IS NULL
                          OR household_key IS NULL
                          OR store_key IS NULL
                          OR date_key IS NULL
                          OR week_key IS NULL
                   )
            FROM expected_sales
            """
        ).fetchone()

        require(
            mapped_count == source_count,
            "Phép nối Dimension làm thay đổi số dòng giao dịch.",
        )
        require(
            missing == 0,
            f"Có {missing:,} giao dịch thiếu khóa hoặc sai ánh xạ tuần.",
        )

        # Nếu có grain trùng, dừng; không DISTINCT hay cộng gộp giao dịch.
        conn.execute(
            """
            ALTER TABLE expected_sales
            ADD PRIMARY KEY (basket_id, product_key)
            """
        )
        conn.execute("ANALYZE expected_sales")

        result = load_dimension(
            conn, batch_id, run_id,
            "fact_sales", "expected_sales",
            ("basket_id", "product_key"),
            COLUMNS,
        )

        # Đối soát riêng từng số đo với nguồn IN_SCOPE.
        totals = {}

        for column in MEASURES:
            source_expression = (
                column if column == "quantity"
                else f"ROUND({column}, 2)"
            )

            source_total = conn.execute(
                f"""
                SELECT COALESCE(SUM({source_expression}), 0)
                FROM sales_in_scope
                """
            ).fetchone()[0]

            target_total = conn.execute(
                f"""
                SELECT COALESCE(SUM({column}), 0)
                FROM dw.fact_sales
                """
            ).fetchone()[0]

            require(
                source_total == target_total,
                f"Tổng {column} không khớp nguồn và Fact.",
            )

            if column == "sales_value":
                require(
                    target_total == EXPECTED["IN_SCOPE"][1],
                    "Tổng sales_value khác mốc FMCG v1.3.",
                )

            conn.execute(
                """
                INSERT INTO audit.reconciliation_result (
                    etl_batch_id, dw_load_id,
                    source_name, target_name, metric_name,
                    source_value, target_value, status, details
                )
                VALUES (
                    %s, %s, 'staging.transactions IN_SCOPE',
                    'dw.fact_sales', %s, %s, %s, 'PASS', %s
                )
                """,
                (
                    batch_id, run_id, f"sum_{column}",
                    source_total, target_total,
                    Jsonb({
                        "money_normalization": (
                            "ROUND từng dòng về 2 chữ số "
                            "sau kiểm tra sai lệch < 0.000001 cent"
                        ) if column in MONEY else "Giữ nguyên quantity",
                    }),
                ),
            )
            totals[column] = target_total

        # Các cột này được GENERATED ALWAYS trong DDL.
        flags = [
            "quantity_zero_flag",
            "quantity_zero_sales_positive_flag",
            "positive_quantity_zero_sales_flag",
            "coupon_above_sales_flag",
            "coupon_match_above_coupon_flag",
            "high_quantity_flag",
        ]

        flag_counts = {
            flag: conn.execute(
                f"SELECT COUNT(*) FROM dw.fact_sales WHERE {flag}"
            ).fetchone()[0]
            for flag in flags
        }

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.fact_sales',
                'FACT_SALES_MEASURES_FLAGS_V1',
                'INFO', 'PASS', 0, %s
            )
            """,
            (
                batch_id, run_id,
                Jsonb({
                    "source_rows": source_count,
                    "mapped_rows": mapped_count,
                    "missing_dimension_rows": missing,
                    "tiny_money_difference_rows": noise_counts,
                    "flag_counts": flag_counts,
                    "timezone": "America/New_York",
                    "source_calendar_id": metadata["source_calendar_id"],
                }),
            ),
        )

    table, total, inserted, unchanged = result
    print(f"\nPASS | {table} | {total:,} dòng")
    print(f"INSERT | {inserted:,} dòng mới")
    print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
    print("PASS | Đối chiếu hai chiều | 0 khác biệt")

    for column, value in totals.items():
        print(f"PASS | Tổng {column} | {value}")

    for flag, count in flag_counts.items():
        print(f"INFO | {flag} | {count:,}")

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
            load_sales(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_fact_sales",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()