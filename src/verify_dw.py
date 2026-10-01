import argparse
from decimal import Decimal
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from dw_run import acquire_lock, PIPELINE_VERSION


# Mốc đối soát của bộ nguồn hiện tại và quy tắc FMCG v1.3.
EXPECTED_COUNTS = {
    "dim_date": 472,
    "dim_week": 53,
    "dim_product": 92351,
    "dim_household": 2469,
    "dim_store": 457,
    "dim_campaign": 27,
    "dim_coupon": 1197,
    "bridge_campaign_household": 6589,
    "bridge_coupon_product": 111332,
    "fact_sales": 1271042,
    "fact_promotion_weekly": 17485242,
    "fact_coupon_redemption": 2102,
}

EXPECTED_MEASURES = {
    "quantity": Decimal("1676406"),
    "sales_value": Decimal("3419948.46"),
    "retail_disc": Decimal("710911.57"),
    "coupon_disc": Decimal("16824.58"),
    "coupon_match_disc": Decimal("4358.46"),
}


def verify_dw(conn, run_id, scope_dir, raw_dir):
    checks = []

    def scalar(query, params=None):
        return conn.execute(query, params).fetchone()[0]

    def record(name, expected, actual):
        require(
            expected is not None and actual is not None,
            f"{name}: kết quả kiểm tra không được NULL.",
        )
        status = "PASS" if expected == actual else "FAIL"
        checks.append((name, expected, actual, status))
        print(
            f"{status} | {name} | "
            f"expected={expected} | actual={actual}",
            flush=True,
        )

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

        # check_inputs tạo input_scope_check từ CSV đã kiểm tra hash.
        # Dùng bảng này để đối soát phạm vi độc lập với Dim_Product.
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

        print("\n=== 1. SỐ DÒNG VÀ BATCH ===", flush=True)

        for table, expected in EXPECTED_COUNTS.items():
            # Tên bảng do chương trình quy định, không lấy từ CLI.
            actual = scalar(f"SELECT COUNT(*) FROM dw.{table}")
            record(f"{table}.row_count", expected, actual)

            if table not in ("dim_date", "dim_week"):
                wrong_batch = scalar(
                    f"""
                    SELECT COUNT(*)
                    FROM dw.{table}
                    WHERE etl_batch_id IS DISTINCT FROM %s
                    """,
                    (batch_id,),
                )
                record(f"{table}.wrong_batch", 0, wrong_batch)

        print("\n=== 2. PHẠM VI FMCG ===", flush=True)

        scope_difference = scalar(
            """
            SELECT COUNT(*)
            FROM input_scope_check c
            LEFT JOIN dw.dim_product p USING (product_id)
            WHERE p.product_key IS NULL
               OR p.scope_status IS DISTINCT FROM c.scope_status
            """
        )
        record("product.scope_vs_csv", 0, scope_difference)

        # Ba mã ngoài CSV đã được xác nhận ở bước nạp sản phẩm.
        extras, invalid_extras = conn.execute(
            """
            SELECT COUNT(*),
                   COUNT(*) FILTER (
                       WHERE p.scope_status <> 'REVIEW'
                          OR NOT p.source_lookup_missing_flag
                   )
            FROM dw.dim_product p
            WHERE NOT EXISTS (
                SELECT 1
                FROM input_scope_check c
                WHERE c.product_id = p.product_id
            )
            """
        ).fetchone()

        record("product.extra_codes", 3, extras)
        record("product.invalid_extra_codes", 0, invalid_extras)

        for table in (
            "dim_product",
            "fact_sales",
            "fact_promotion_weekly",
        ):
            bad_version = scalar(
                f"""
                SELECT COUNT(*)
                FROM dw.{table}
                WHERE scope_rule_version IS DISTINCT FROM %s
                """,
                (metadata["scope_rule_version"],),
            )
            record(f"{table}.wrong_scope_version", 0, bad_version)

        for table in ("fact_sales", "fact_promotion_weekly"):
            bad_scope = scalar(
                f"""
                SELECT COUNT(*)
                FROM dw.{table} f
                LEFT JOIN dw.dim_product p USING (product_key)
                LEFT JOIN input_scope_check c
                  ON c.product_id = p.product_id
                WHERE p.product_key IS NULL
                   OR c.scope_status IS DISTINCT FROM 'IN_SCOPE'
                   OR p.source_lookup_missing_flag
                """
            )
            record(f"{table}.invalid_scope", 0, bad_scope)

        print("\n=== 3. RÀNG BUỘC KHÓA ===", flush=True)

        # Đối chiếu cấu trúc đã chốt trong DDL.
        constraint_counts = dict(
            conn.execute(
                """
                SELECT c.contype, COUNT(*)
                FROM pg_constraint c
                JOIN pg_class t ON t.oid = c.conrelid
                JOIN pg_namespace n ON n.oid = t.relnamespace
                WHERE n.nspname = 'dw'
                GROUP BY c.contype
                """
            ).fetchall()
        )

        for kind, expected in (("p", 12), ("u", 12), ("f", 31)):
            record(
                f"constraints.{kind}",
                expected,
                constraint_counts.get(kind, 0),
            )

        invalid_constraints = scalar(
            """
            SELECT COUNT(*)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = 'dw'
              AND NOT c.convalidated
            """
        )
        record("constraints.not_validated", 0, invalid_constraints)

        invalid_indexes = scalar(
            """
            SELECT COUNT(*)
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            LEFT JOIN pg_index i ON i.indexrelid = c.conindid
            WHERE n.nspname = 'dw'
              AND c.contype IN ('p', 'u')
              AND (
                  i.indexrelid IS NULL
                  OR NOT i.indisvalid
                  OR NOT i.indisready
                  OR NOT i.indisunique
              )
            """
        )
        record("constraints.invalid_key_indexes", 0, invalid_indexes)

        # Kiểm tra dữ liệu thực tế cho tất cả FK, kể cả FK ghép.
        # PostgreSQL tạo tên bảng/cột đã quote bằng format('%I').
        fk_queries = conn.execute(
            """
            SELECT c.conname,
                   format(
                       'SELECT COUNT(*) FROM %s d WHERE %s '
                       'AND NOT EXISTS '
                       '(SELECT 1 FROM %s p WHERE %s)',
                       c.conrelid::regclass,
                       string_agg(
                           format('d.%I IS NOT NULL', a.attname),
                           ' AND ' ORDER BY k.ord
                       ),
                       c.confrelid::regclass,
                       string_agg(
                           format('p.%I = d.%I', b.attname, a.attname),
                           ' AND ' ORDER BY k.ord
                       )
                   )
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            CROSS JOIN LATERAL
                unnest(c.conkey, c.confkey) WITH ORDINALITY
                AS k(src_col, dst_col, ord)
            JOIN pg_attribute a
              ON a.attrelid = c.conrelid
             AND a.attnum = k.src_col
            JOIN pg_attribute b
              ON b.attrelid = c.confrelid
             AND b.attnum = k.dst_col
            WHERE n.nspname = 'dw'
              AND c.contype = 'f'
            GROUP BY c.oid, c.conname, c.conrelid, c.confrelid
            ORDER BY c.conname
            """
        ).fetchall()

        for name, query in fk_queries:
            record(f"fk.{name}", 0, scalar(query))

        print("\n=== 4. SỐ ĐO BÁN HÀNG ===", flush=True)

        columns = list(EXPECTED_MEASURES)
        source_sums = ", ".join(
            (
                "COALESCE(SUM(t.quantity), 0)"
                if column == "quantity"
                else f"COALESCE(SUM(ROUND(t.{column}, 2)), 0)"
            )
            for column in columns
        )
        target_sums = ", ".join(
            f"COALESCE(SUM({column}), 0)"
            for column in columns
        )

        source = conn.execute(
            f"""
            SELECT COUNT(*), {source_sums}
            FROM staging.stg_transactions t
            JOIN input_scope_check c USING (product_id)
            WHERE t.etl_batch_id = %s
              AND c.scope_status = 'IN_SCOPE'
            """,
            (batch_id,),
        ).fetchone()

        target = conn.execute(
            f"SELECT COUNT(*), {target_sums} FROM dw.fact_sales"
        ).fetchone()

        record("sales.source_vs_target_rows", source[0], target[0])

        for index, column in enumerate(columns, start=1):
            record(
                f"sales.{column}.source_vs_target",
                source[index],
                target[index],
            )
            record(
                f"sales.{column}.baseline",
                EXPECTED_MEASURES[column],
                target[index],
            )

        print("\n=== 5. NGÀY VÀ TUẦN ===", flush=True)

        wrong_dates = scalar(
            """
            SELECT COUNT(*)
            FROM dw.fact_sales f
            LEFT JOIN dw.dim_date d USING (date_key)
            LEFT JOIN dw.dim_week w USING (week_key)
            WHERE d.full_date IS DISTINCT FROM
                  (f.transaction_timestamp
                   AT TIME ZONE 'America/New_York')::date
               OR w.week_key IS NULL
               OR w.source_calendar_id IS DISTINCT FROM 'CJ_2017'
               OR d.full_date NOT BETWEEN
                  DATE '2017-01-01' AND DATE '2017-12-31'
               OR d.full_date NOT BETWEEN
                  w.coverage_start_date AND w.coverage_end_date
            """
        )
        record("sales.date_week_mapping", 0, wrong_dates)

        wrong_weeks = scalar(
            """
            SELECT COUNT(*)
            FROM dw.dim_week
            WHERE source_calendar_id <> 'CJ_2017'
               OR week_start_date <>
                  DATE '2016-12-26' + (source_week - 1) * 7
               OR week_end_date <> week_start_date + 6
               OR coverage_start_date <>
                  GREATEST(week_start_date, DATE '2017-01-01')
               OR coverage_end_date <>
                  LEAST(week_end_date, DATE '2017-12-31')
            """
        )
        record("week.calendar_mapping", 0, wrong_weeks)

        print("\n=== 6. NGUỒN KHUYẾN MÃI ===", flush=True)

        promotion_source = scalar(
            """
            SELECT COUNT(*)
            FROM staging.stg_promotions p
            JOIN input_scope_check c USING (product_id)
            WHERE p.etl_batch_id = %s
              AND c.scope_status = 'IN_SCOPE'
            """,
            (batch_id,),
        )
        promotion_target = scalar(
            """
            SELECT COALESCE(SUM(source_row_count), 0)
            FROM dw.fact_promotion_weekly
            """
        )
        record(
            "promotion.represented_source_rows",
            promotion_source,
            promotion_target,
        )
        record("promotion.source_baseline", 17488986, promotion_source)

        print("\n=== 7. JOIN KHÔNG NHÂN DOANH SỐ ===", flush=True)

        joined_sums = ", ".join(
            f"COALESCE(SUM(f.{column}), 0)"
            for column in columns
        )
        joined = conn.execute(
            f"""
            SELECT COUNT(*),
                   {joined_sums},
                   COUNT(*) FILTER (
                       WHERE p.promotion_weekly_key IS NULL
                   )
            FROM dw.fact_sales f
            LEFT JOIN dw.fact_promotion_weekly p
              ON p.product_key = f.product_key
             AND p.store_key = f.store_key
             AND p.week_key = f.week_key
            """
        ).fetchone()

        record("sales_promotion.join_rows", target[0], joined[0])

        for index, column in enumerate(columns, start=1):
            record(
                f"sales_promotion.{column}",
                target[index],
                joined[index],
            )

        unmatched = joined[-1]
        print(
            f"INFO | Giao dịch không khớp khuyến mãi | {unmatched:,}",
            flush=True,
        )
        # Không khớp không tự đồng nghĩa với không có khuyến mãi.

        print("\n=== 8. COUPON REDEMPTION ===", flush=True)

        redemption_source = scalar(
            """
            SELECT COUNT(*)
            FROM staging.stg_coupon_redemptions
            WHERE etl_batch_id = %s
            """,
            (batch_id,),
        )
        redemption_target = scalar(
            """
            SELECT COALESCE(SUM(redemption_record_count), 0)
            FROM dw.fact_coupon_redemption
            """
        )
        record(
            "redemption.source_vs_target",
            redemption_source,
            redemption_target,
        )

        invalid_redemptions = scalar(
            """
            SELECT COUNT(*)
            FROM dw.fact_coupon_redemption r
            LEFT JOIN dw.dim_date d
              ON d.date_key = r.redemption_date_key
            LEFT JOIN dw.dim_campaign c
              ON c.campaign_key = r.campaign_key
            WHERE d.date_key IS NULL
               OR c.campaign_key IS NULL
               OR d.full_date NOT BETWEEN c.start_date AND c.end_date
               OR NOT EXISTS (
                   SELECT 1
                   FROM dw.bridge_campaign_household b
                   WHERE b.campaign_key = r.campaign_key
                     AND b.household_key = r.household_key
               )
            """
        )
        record("redemption.invalid_links_dates", 0, invalid_redemptions)

        # Ghi kết quả kể cả khi một phép đối soát trả FAIL.
        for name, expected, actual, status in checks:
            conn.execute(
                """
                INSERT INTO audit.reconciliation_result (
                    etl_batch_id, dw_load_id,
                    source_name, target_name, metric_name,
                    source_value, target_value, status, details
                )
                VALUES (
                    %s, %s, 'source_or_expected', 'dw',
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    batch_id,
                    run_id,
                    f"DW_VERIFY_V1.{name}",
                    expected,
                    actual,
                    status,
                    Jsonb({"step": "verify_dw"}),
                ),
            )

        failed = sum(status == "FAIL" for *_, status in checks)

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw', 'DW_VERIFY_V1',
                'ERROR', %s, %s, %s
            )
            """,
            (
                batch_id,
                run_id,
                "FAIL" if failed else "PASS",
                failed,
                Jsonb({
                    "step": "verify_dw",
                    "total_checks": len(checks),
                    "failed_checks": failed,
                    "affected_rows_unit": "failed_checks",
                    "sales_without_promotion_match": unmatched,
                    "scope_file_sha256": metadata["scope_file_sha256"],
                    "source_manifest_hash": metadata["source_manifest_hash"],
                }),
            ),
        )

    # Transaction đã commit kết quả audit.
    print(
        f"\nDW VERIFY: {'FAIL' if failed else 'PASS'}"
        f" | {len(checks)} kiểm tra | {failed} lỗi",
        flush=True,
    )
    print(f"dw_load_id={run_id} vẫn RUNNING.")
    return failed == 0


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
        passed = verify_dw(
            conn,
            args.dw_load_id,
            args.scope_dir.resolve(),
            args.raw_dir.resolve(),
        )

    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()