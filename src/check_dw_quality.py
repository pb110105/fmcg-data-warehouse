import argparse
import json
from pathlib import Path

from psycopg import sql
from psycopg.types.json import Jsonb

from load_staging import ROOT, FILES, connect_db
from check_dw_inputs import check_inputs
from dw_run import acquire_lock


PREFIX = "DQ_V1_"

KEYS = {
    "products": ["product_id"],
    "demographics": ["household_id"],
    "campaign_descriptions": ["campaign_id"],
    "campaigns": ["campaign_id", "household_id"],
    "coupons": ["campaign_id", "coupon_upc", "product_id"],
    "coupon_redemptions": [
        "household_id", "coupon_upc", "campaign_id"
    ],
    "transactions": [
        "household_id", "store_id", "basket_id", "product_id"
    ],
    "promotions": ["product_id", "store_id"],
}

DESCRIPTIONS = {
    "products": [
        "manufacturer_id", "department", "brand",
        "product_category", "product_type", "package_size",
    ],
    "demographics": [
        "age", "income", "home_ownership", "marital_status",
        "household_size", "household_comp", "kids_count",
    ],
    "campaign_descriptions": ["campaign_type"],
}

MONEY = [
    "sales_value", "retail_disc",
    "coupon_disc", "coupon_match_disc",
]


def check_rule(conn, results, table, code, severity, query, action):
    """
    query trả các dòng hoặc nhóm có vấn đề.
    affected_rows = số dòng kết quả của query.
    Với truy vấn GROUP BY, đây là số nhóm, không phải số dòng dư.
    """
    statement = f"""
        WITH issues AS MATERIALIZED (
            {query}
        )
        SELECT
            (SELECT COUNT(*) FROM issues),
            COALESCE(
                (
                    SELECT jsonb_agg(to_jsonb(sample))
                    FROM (
                        SELECT * FROM issues LIMIT 5
                    ) sample
                ),
                '[]'::jsonb
            )
    """

    affected, samples = conn.execute(statement).fetchone()
    status = (
        "FAIL"
        if affected > 0 and severity in ("ERROR", "WARNING")
        else "PASS"
    )

    results.append({
        "table": table,
        "code": PREFIX + code,
        "severity": severity,
        "status": status,
        "affected": affected,
        "details": {
            "action": action,
            "count_unit": "rows_returned_by_rule",
            "samples": samples,
        },
    })

    label = (
        "BLOCK" if severity == "ERROR" and affected
        else "WARN" if severity == "WARNING" and affected
        else "INFO" if severity == "INFO"
        else "PASS"
    )
    print(f"{label} | {code} | {affected:,}", flush=True)


def create_normalized_views(conn, batch_id):
    """
    View tạm chỉ tồn tại trong kết nối hiện tại.
    Chuẩn hóa thuộc tính mô tả; không sửa mã định danh.
    """
    for _, staging_table in FILES:
        name = staging_table.removeprefix("stg_")

        columns = conn.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'staging'
              AND table_name = %s
            ORDER BY ordinal_position
            """,
            (staging_table,),
        ).fetchall()

        expressions = []
        for (column,) in columns:
            identifier = sql.Identifier(column)

            if column in DESCRIPTIONS.get(name, []):
                expression = sql.SQL(
                    "NULLIF(BTRIM({}), '') AS {}"
                ).format(identifier, identifier)
            else:
                expression = identifier

            expressions.append(expression)

        conn.execute(
            sql.SQL(
                "CREATE TEMP VIEW {} AS "
                "SELECT {} FROM {} WHERE etl_batch_id = {}"
            ).format(
                sql.Identifier("q_" + name),
                sql.SQL(", ").join(expressions),
                sql.Identifier("staging", staging_table),
                sql.Literal(batch_id),
            )
        )


def run_rules(conn, results):
    def rule(table, code, severity, query, action):
        check_rule(
            conn, results, table, code, severity, query, action
        )

    # -----------------------------------------------------
    # A. MÃ BẮT BUỘC
    # -----------------------------------------------------
    for table, columns in KEYS.items():
        condition = " OR ".join(
            f"{column} IS NULL OR BTRIM({column}) = ''"
            for column in columns
        )

        rule(
            table,
            f"{table}_required_keys",
            "ERROR",
            f"""
            SELECT staging_row_id, source_row_number
            FROM q_{table}
            WHERE {condition}
            """,
            "Chặn nạp; không tự tạo mã thay thế cho mã rỗng.",
        )

    # -----------------------------------------------------
    # B. TRÙNG KHÓA VÀ XUNG ĐỘT THUỘC TÍNH
    # -----------------------------------------------------
    for table, key in [
        ("products", "product_id"),
        ("demographics", "household_id"),
        ("campaign_descriptions", "campaign_id"),
    ]:
        attributes = list(DESCRIPTIONS[table])
        if table == "campaign_descriptions":
            attributes += ["start_date", "end_date"]

        fields = ", ".join(attributes)

        rule(
            table,
            f"{table}_conflicting_attributes",
            "ERROR",
            f"""
            SELECT {key}, COUNT(*) AS source_rows
            FROM q_{table}
            GROUP BY {key}
            HAVING COUNT(DISTINCT ROW({fields})) > 1
            """,
            "Chặn nạp nếu một mã có thuộc tính chuẩn hóa mâu thuẫn.",
        )

        rule(
            table,
            f"{table}_duplicate_keys",
            "WARNING",
            f"""
            SELECT {key}, COUNT(*) AS source_rows
            FROM q_{table}
            GROUP BY {key}
            HAVING COUNT(*) > 1
            """,
            "Chỉ gộp dòng giống nhau khi nạp Dimension; "
            "xung đột thuộc tính phải được xử lý trước.",
        )

    duplicate_rules = [
        (
            "transactions", "basket_id, product_id", "ERROR",
            "Chặn vì trùng grain Fact_Sales.",
        ),
        (
            "coupon_redemptions",
            "household_id, coupon_upc, campaign_id, redemption_date",
            "ERROR",
            "Chặn vì trùng grain Fact_Coupon_Redemption.",
        ),
        (
            "campaigns", "campaign_id, household_id", "WARNING",
            "Lấy cặp phân biệt khi nạp Bridge.",
        ),
        (
            "coupons", "campaign_id, coupon_upc, product_id", "WARNING",
            "Lấy bộ ba phân biệt khi nạp Bridge.",
        ),
        (
            "promotions", "product_id, store_id, week", "WARNING",
            "Tổng hợp toàn bộ mã hỗ trợ trong nhóm; không chọn dòng đầu.",
        ),
    ]

    for table, fields, severity, action in duplicate_rules:
        rule(
            table,
            f"{table}_duplicate_grain",
            severity,
            f"""
            SELECT {fields}, COUNT(*) AS source_rows,
                   COUNT(*) - 1 AS excess_rows
            FROM q_{table}
            GROUP BY {fields}
            HAVING COUNT(*) > 1
            """,
            action + " Số đếm hiển thị là số nhóm.",
        )

    rule(
        "transactions", "basket_conflict", "ERROR",
        """
        SELECT basket_id
        FROM q_transactions
        GROUP BY basket_id
        HAVING COUNT(DISTINCT household_id) > 1
            OR COUNT(DISTINCT store_id) > 1
        """,
        "Chặn nếu một giỏ thuộc nhiều hộ hoặc nhiều cửa hàng.",
    )

    # -----------------------------------------------------
    # C. SỐ ĐO VÀ ĐỘ CHÍNH XÁC TIỀN
    # -----------------------------------------------------
    measures = ["quantity"] + MONEY
    invalid = " OR ".join(
        f"""(
            {c} IS NULL
            OR {c}::TEXT IN ('NaN', 'Infinity', '-Infinity')
            OR {c} < 0
        )"""
        for c in measures
    )

    rule(
        "transactions", "invalid_measures", "ERROR",
        f"""
        SELECT staging_row_id, basket_id, product_id
        FROM q_transactions
        WHERE {invalid}
        """,
        "Chặn khi số đo thiếu, âm hoặc không hữu hạn.",
    )

    for column in MONEY:
        rule(
            "transactions",
            f"{column}_cent_precision",
            "ERROR",
            f"""
            SELECT staging_row_id, basket_id, product_id, {column}
            FROM q_transactions
            WHERE {column}::TEXT
                      NOT IN ('NaN', 'Infinity', '-Infinity')
              AND ABS(
                  {column} * 100 - ROUND({column} * 100)
              ) >= 0.000001
            """,
            "Chặn nếu sai lệch tới cent vượt ngưỡng; không tự sửa.",
        )

        rule(
            "transactions",
            f"{column}_tiny_decimal_difference",
            "INFO",
            f"""
            SELECT staging_row_id, {column},
                   ROUND({column}, 2) AS normalized_value
            FROM q_transactions
            WHERE {column}::TEXT
                      NOT IN ('NaN', 'Infinity', '-Infinity')
              AND {column} <> ROUND({column}, 2)
              AND ABS(
                  {column} * 100 - ROUND({column} * 100)
              ) < 0.000001
            """,
            "Cho phép chuẩn hóa về cent ở lớp DW; giữ nguyên Staging.",
        )

    # View số tiền chuẩn hóa cho các kiểm tra nghiệp vụ.
    # Giá trị không đạt vẫn giữ nguyên và đã có ERROR ở trên.
    expressions = [
        f"""
        CASE
            WHEN {c}::TEXT NOT IN ('NaN', 'Infinity', '-Infinity')
             AND ABS({c} * 100 - ROUND({c} * 100)) < 0.000001
            THEN ROUND({c}, 2)
            ELSE {c}
        END AS {c}
        """
        for c in MONEY
    ]

    conn.execute(
        f"""
        CREATE TEMP VIEW q_sales_normalized AS
        SELECT staging_row_id, basket_id, product_id, quantity,
               {", ".join(expressions)}
        FROM q_transactions
        """
    )

    warnings = {
        "quantity_zero": "quantity = 0",
        "sales_zero": "sales_value = 0",
        "zero_quantity_positive_sales":
            "quantity = 0 AND sales_value > 0",
        "positive_quantity_zero_sales":
            "quantity > 0 AND sales_value = 0",
        "coupon_above_sales": "coupon_disc > sales_value",
        "match_above_coupon": "coupon_match_disc > coupon_disc",
        "match_above_retail": "coupon_match_disc > retail_disc",
        "high_quantity": "quantity > 100",
        "fractional_quantity": "quantity <> TRUNC(quantity)",
    }

    for name, condition in warnings.items():
        rule(
            "transactions",
            "fmcg_" + name,
            "WARNING",
            f"""
            SELECT t.*
            FROM q_sales_normalized t
            JOIN input_scope_check s USING (product_id)
            WHERE s.scope_status = 'IN_SCOPE'
              AND ({condition})
            """,
            "Giữ bản ghi; gắn cờ hoặc áp dụng điều kiện KPI. "
            "Phạm vi kiểm tra: IN_SCOPE.",
        )

    # -----------------------------------------------------
    # D. NGÀY VÀ TUẦN
    # -----------------------------------------------------
    rule(
        "transactions", "date_week_mapping", "ERROR",
        """
        SELECT t.staging_row_id, t.week, t.transaction_timestamp
        FROM q_transactions t
        LEFT JOIN dw.dim_week w
          ON w.source_calendar_id = 'CJ_2017'
         AND w.source_week = t.week
        LEFT JOIN dw.dim_date d
          ON d.full_date = (
              t.transaction_timestamp
              AT TIME ZONE 'America/New_York'
          )::DATE
        WHERE t.transaction_timestamp IS NULL
           OR NOT isfinite(t.transaction_timestamp)
           OR w.week_key IS NULL
           OR d.date_key IS NULL
           OR (t.transaction_timestamp
               AT TIME ZONE 'America/New_York')::DATE
              NOT BETWEEN w.coverage_start_date AND w.coverage_end_date
        """,
        "Chặn nếu không ánh xạ được ngày/tuần nguồn.",
    )

    rule(
        "promotions", "promotion_week_mapping", "ERROR",
        """
        SELECT p.staging_row_id, p.week
        FROM q_promotions p
        LEFT JOIN dw.dim_week w
          ON w.source_calendar_id = 'CJ_2017'
         AND w.source_week = p.week
        WHERE w.week_key IS NULL
        """,
        "Chặn nếu tuần khuyến mãi không có trong CJ_2017.",
    )

    rule(
        "campaign_descriptions", "campaign_dates_type", "ERROR",
        """
        SELECT staging_row_id, campaign_id
        FROM q_campaign_descriptions
        WHERE campaign_type IS NULL
           OR start_date IS NULL OR end_date IS NULL
           OR NOT isfinite(start_date) OR NOT isfinite(end_date)
           OR start_date > end_date
           OR NOT EXISTS (
               SELECT 1 FROM dw.dim_date d
               WHERE d.full_date = start_date
           )
           OR NOT EXISTS (
               SELECT 1 FROM dw.dim_date d
               WHERE d.full_date = end_date
           )
        """,
        "Chặn nếu loại chiến dịch hoặc khoảng ngày không hợp lệ.",
    )

    # -----------------------------------------------------
    # E. LIÊN KẾT
    # -----------------------------------------------------
    for table in ["campaigns", "coupons", "coupon_redemptions"]:
        rule(
            table, f"{table}_missing_campaign", "ERROR",
            f"""
            SELECT t.staging_row_id, t.campaign_id
            FROM q_{table} t
            WHERE NOT EXISTS (
                SELECT 1 FROM q_campaign_descriptions c
                WHERE c.campaign_id = t.campaign_id
            )
            """,
            "Chặn khi thiếu mô tả chiến dịch.",
        )

    rule(
        "coupon_redemptions", "redemption_coupon_link", "ERROR",
        """
        SELECT r.staging_row_id, r.campaign_id, r.coupon_upc
        FROM q_coupon_redemptions r
        WHERE NOT EXISTS (
            SELECT 1 FROM q_coupons c
            WHERE c.campaign_id = r.campaign_id
              AND c.coupon_upc = r.coupon_upc
        )
        """,
        "Chặn khi không tìm được cặp chiến dịch–coupon.",
    )

    rule(
        "coupon_redemptions", "redemption_household_campaign", "ERROR",
        """
        SELECT r.staging_row_id, r.household_id, r.campaign_id
        FROM q_coupon_redemptions r
        WHERE NOT EXISTS (
            SELECT 1 FROM q_campaigns c
            WHERE c.campaign_id = r.campaign_id
              AND c.household_id = r.household_id
        )
        """,
        "Chặn để kiểm tra liên kết hộ nhận chiến dịch.",
    )

    rule(
        "coupon_redemptions", "redemption_dates", "ERROR",
        """
        SELECT r.staging_row_id, r.redemption_date, r.campaign_id
        FROM q_coupon_redemptions r
        WHERE r.redemption_date IS NULL
           OR NOT isfinite(r.redemption_date)
           OR NOT EXISTS (
               SELECT 1 FROM dw.dim_date d
               WHERE d.full_date = r.redemption_date
           )
           OR NOT EXISTS (
               SELECT 1 FROM q_campaign_descriptions c
               WHERE c.campaign_id = r.campaign_id
                 AND r.redemption_date BETWEEN c.start_date AND c.end_date
           )
        """,
        "Chặn nếu ngày đổi coupon không hợp lệ hoặc ngoài chiến dịch.",
    )

    for table in ["transactions", "promotions", "coupons"]:
        rule(
            table, f"{table}_missing_product_lookup", "WARNING",
            f"""
            SELECT t.staging_row_id, t.product_id
            FROM q_{table} t
            WHERE NOT EXISTS (
                SELECT 1 FROM q_products p
                WHERE p.product_id = t.product_id
            )
            """,
            "Giữ mã; tạo Dimension thiếu thông tin và giữ REVIEW.",
        )

    rule(
        "transactions", "missing_demographics", "WARNING",
        """
        SELECT t.staging_row_id, t.household_id
        FROM q_transactions t
        WHERE NOT EXISTS (
            SELECT 1 FROM q_demographics d
            WHERE d.household_id = t.household_id
        )
        """,
        "Giữ hộ và giao dịch; thuộc tính nhân khẩu học để NULL.",
    )

    # -----------------------------------------------------
    # F. THUỘC TÍNH THIẾU VÀ MÃ KHUYẾN MÃI
    # -----------------------------------------------------
    for table, columns in [
        ("products", ["product_category", "product_type", "package_size"]),
        ("demographics", ["home_ownership", "marital_status"]),
    ]:
        for column in columns:
            rule(
                table, f"{table}_{column}_missing", "WARNING",
                f"""
                SELECT staging_row_id
                FROM q_{table}
                WHERE {column} IS NULL
                """,
                "Giữ NULL sau chuẩn hóa; không tự suy diễn.",
            )

    rule(
        "promotions", "unknown_promotion_codes", "WARNING",
        """
        SELECT staging_row_id, display_location, mailer_location
        FROM q_promotions
        WHERE display_location IS NULL
           OR display_location NOT IN
              ('0','1','2','3','4','5','6','7','9','A')
           OR mailer_location IS NULL
           OR mailer_location NOT IN
              ('0','A','C','D','F','H','J','L','P','X','Z')
        """,
        "Giữ mã gốc; gắn unknown flag, không tự coi là không khuyến mãi.",
    )


def save_results(conn, batch_id, run_id, results):
    # Các lần kiểm tra được giữ để truy vết, không xóa log cũ.
    with conn.transaction():
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO audit.data_quality_result (
                    etl_batch_id, dw_load_id, table_name,
                    rule_code, severity, status,
                    affected_rows, details
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                [
                    (
                        batch_id, run_id, result["table"],
                        result["code"], result["severity"],
                        result["status"], result["affected"],
                        Jsonb(result["details"]),
                    )
                    for result in results
                ],
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dw-load-id", type=int, required=True)
    parser.add_argument(
        "--scope-dir", type=Path,
        default=ROOT / "data/landing/fmcg_classification_v1_3",
    )
    parser.add_argument(
        "--raw-dir", type=Path,
        default=ROOT / "data/raw/complete_journey",
    )
    args = parser.parse_args()

    results = []
    runtime_error = None

    with connect_db() as conn:
        acquire_lock(conn)

        run = conn.execute(
            """
            SELECT source_batch_id, pipeline_version,
                   scope_rule_version, scope_file_sha256,
                   source_calendar_id, status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            """,
            (args.dw_load_id,),
        ).fetchone()

        if run is None or run[5] != "RUNNING":
            raise ValueError("DW load phải tồn tại và đang RUNNING.")

        batch_id = run[0]

        try:
            with conn.transaction():
                conn.execute(
                    "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
                )

                metadata = check_inputs(
                    conn, batch_id,
                    args.scope_dir.resolve(),
                    args.raw_dir.resolve(),
                )

                if (
                    run[1] != "dw-1.0"
                    or run[2] != metadata["scope_rule_version"]
                    or run[3] != metadata["scope_file_sha256"]
                    or run[4] != metadata["source_calendar_id"]
                ):
                    raise ValueError("Đầu vào không khớp nhật ký DW.")

                create_normalized_views(conn, batch_id)
                run_rules(conn, results)

        except Exception as exc:
            runtime_error = f"{type(exc).__name__}: {exc}"
            results.append({
                "table": "DW_PIPELINE",
                "code": PREFIX + "execution_error",
                "severity": "ERROR",
                "status": "FAIL",
                "affected": 0,
                "details": {
                    "error": runtime_error,
                    "affected_rows_known": False,
                },
            })

        # Lưu log sau khi transaction kiểm tra đã kết thúc.
        # Lỗi SQL không làm mất các kết quả kiểm tra đã thu được.
        save_results(conn, batch_id, args.dw_load_id, results)

        blockers = [
            r for r in results
            if r["severity"] == "ERROR" and r["status"] == "FAIL"
        ]
        warnings = [
            r for r in results
            if r["severity"] == "WARNING" and r["status"] == "FAIL"
        ]

        if blockers:
            message = runtime_error or (
                "Các kiểm tra chặn: "
                + ", ".join(r["code"] for r in blockers)
            )

            conn.execute(
                """
                UPDATE audit.dw_load
                SET status = 'FAILED',
                    finished_at = clock_timestamp(),
                    error_message = %s
                WHERE dw_load_id = %s AND status = 'RUNNING'
                """,
                (message, args.dw_load_id),
            )

            print(f"\nDQ BLOCKED | {len(blockers)} kiểm tra chặn")
            print(message)
            raise SystemExit(1)

        print(
            f"\nDQ PASS | {len(results)} kiểm tra | "
            f"{len(warnings)} quy tắc có cảnh báo"
        )
        print(
            f"dw_load_id={args.dw_load_id} vẫn RUNNING; "
            "chưa đánh dấu toàn bộ DW thành công."
        )


if __name__ == "__main__":
    main()