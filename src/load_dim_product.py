import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION


COLUMNS = [
    "product_id",
    "manufacturer_id",
    "department",
    "brand",
    "product_category",
    "product_type",
    "package_size",
    "scope_status",
    "scope_rule_version",
    "source_lookup_missing_flag",
    "etl_batch_id",
]


def load_product(conn, run_id, scope_dir, raw_dir):
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

        # check_dw_quality.py lưu một bộ kết quả trong cùng
        # transaction, nên chúng có chung checked_at.
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

        # Mốc của phiên bản check_dw_quality.py hiện tại.
        require(
            dq == (57, 57, 0),
            f"Chưa có bộ 57 kiểm tra DQ đầy đủ, không lỗi chặn: {dq}",
        )
        print("PASS | DQ đầu vào | 57 kiểm tra, không lỗi chặn")

        create_normalized_views(conn, batch_id)

        # Tạo danh mục đã chuẩn hóa. Không tự chọn một dòng
        # khi cùng mã có thuộc tính mâu thuẫn.
        conn.execute(
            """
            CREATE TEMP TABLE product_lookup ON COMMIT DROP AS
            SELECT DISTINCT
                   product_id,
                   manufacturer_id,
                   department,
                   brand,
                   product_category,
                   product_type,
                   package_size
            FROM q_products
            """
        )

        conflicts = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT product_id
                FROM product_lookup
                GROUP BY product_id
                HAVING COUNT(*) > 1
            ) x
            """
        ).fetchone()[0]

        require(conflicts == 0, "Danh mục có thuộc tính mâu thuẫn.")

        conn.execute(
            "ALTER TABLE product_lookup ADD PRIMARY KEY (product_id)"
        )

        # Hợp mã từ toàn bộ các nguồn có product_id.
        conn.execute(
            """
            CREATE TEMP TABLE product_ids ON COMMIT DROP AS
            SELECT product_id FROM q_products
            UNION
            SELECT product_id FROM q_transactions
            UNION
            SELECT product_id FROM q_promotions
            UNION
            SELECT product_id FROM q_coupons
            """
        )

        invalid_ids = conn.execute(
            """
            SELECT COUNT(*)
            FROM product_ids
            WHERE product_id IS NULL OR BTRIM(product_id) = ''
            """
        ).fetchone()[0]

        require(invalid_ids == 0, "Có mã sản phẩm NULL hoặc rỗng.")
        conn.execute(
            "ALTER TABLE product_ids ADD PRIMARY KEY (product_id)"
        )

        # CSV đã được check_inputs đọc, kiểm tra hash và nạp vào
        # bảng tạm input_scope_check. Dùng lại đúng bản đó.
        conn.execute(
            """
            CREATE TEMP TABLE expected_product ON COMMIT DROP AS
            SELECT
                i.product_id,
                p.manufacturer_id,
                p.department,
                p.brand,
                p.product_category,
                p.product_type,
                p.package_size,
                CASE
                    WHEN p.product_id IS NULL THEN 'REVIEW'
                    ELSE c.scope_status
                END AS scope_status,
                %s::text AS scope_rule_version,
                (p.product_id IS NULL) AS source_lookup_missing_flag,
                %s::bigint AS etl_batch_id
            FROM product_ids i
            LEFT JOIN product_lookup p USING (product_id)
            LEFT JOIN input_scope_check c USING (product_id)
            """,
            (metadata["scope_rule_version"], batch_id),
        )

        missing_scope = conn.execute(
            """
            SELECT COUNT(*)
            FROM expected_product
            WHERE scope_status IS NULL
            """
        ).fetchone()[0]

        require(
            missing_scope == 0,
            "Có sản phẩm trong lookup nhưng chưa có phân loại.",
        )

        conn.execute(
            "ALTER TABLE expected_product ADD PRIMARY KEY (product_id)"
        )

        extra_review = conn.execute(
            """
            SELECT COUNT(*)
            FROM expected_product e
            WHERE NOT EXISTS (
                SELECT 1 FROM input_scope_check c
                WHERE c.product_id = e.product_id
            )
            """
        ).fetchone()[0]

        # Chặn ghi đè âm thầm nếu DW đang chứa dữ liệu khác.
        # Bước này dành cho bộ nguồn/phiên bản hiện tại;
        # cập nhật sang phiên bản mới cần quy trình riêng.
        target_values = ", ".join(f"d.{c}" for c in COLUMNS)
        expected_values = ", ".join(f"e.{c}" for c in COLUMNS)

        conflicts = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM dw.dim_product d
            JOIN expected_product e USING (product_id)
            WHERE ROW({target_values})
                  IS DISTINCT FROM ROW({expected_values})
            """
        ).fetchone()[0]

        require(
            conflicts == 0,
            f"DW có {conflicts} sản phẩm khác dữ liệu dự kiến; dừng nạp.",
        )

        extras = conn.execute(
            """
            SELECT COUNT(*)
            FROM dw.dim_product d
            WHERE NOT EXISTS (
                SELECT 1 FROM expected_product e
                WHERE e.product_id = d.product_id
            )
            """
        ).fetchone()[0]

        require(
            extras == 0,
            "DW chứa mã ngoài bộ nguồn hiện tại; cần kiểm tra trước.",
        )

        before = conn.execute(
            "SELECT COUNT(*) FROM dw.dim_product"
        ).fetchone()[0]

        columns = ", ".join(COLUMNS)

        # Chỉ thêm mã chưa tồn tại: chạy lại không sửa khóa,
        # thuộc tính hoặc loaded_at của các dòng đã nạp.
        inserted = conn.execute(
            f"""
            INSERT INTO dw.dim_product ({columns})
            SELECT {", ".join(f"e.{c}" for c in COLUMNS)}
            FROM expected_product e
            WHERE NOT EXISTS (
                SELECT 1 FROM dw.dim_product d
                WHERE d.product_id = e.product_id
            )
            ORDER BY e.product_id
            """
        ).rowcount

        # Đối chiếu toàn bộ cột nghiệp vụ theo hai chiều.
        difference = conn.execute(
            f"""
            SELECT COUNT(*)
            FROM (
                (
                    SELECT {columns} FROM expected_product
                    EXCEPT
                    SELECT {columns} FROM dw.dim_product
                )
                UNION ALL
                (
                    SELECT {columns} FROM dw.dim_product
                    EXCEPT
                    SELECT {columns} FROM expected_product
                )
            ) differences
            """
        ).fetchone()[0]

        require(difference == 0, "Dim_Product không khớp dữ liệu dự kiến.")

        expected_count = conn.execute(
            "SELECT COUNT(*) FROM expected_product"
        ).fetchone()[0]

        actual_count = conn.execute(
            "SELECT COUNT(*) FROM dw.dim_product"
        ).fetchone()[0]

        require(
            expected_count == actual_count == before + inserted,
            "Số dòng Dim_Product không khớp.",
        )

        summary = conn.execute(
            """
            SELECT scope_status,
                   COUNT(*) AS product_count,
                   COUNT(*) FILTER (
                       WHERE source_lookup_missing_flag
                   ) AS missing_lookup_count
            FROM dw.dim_product
            GROUP BY scope_status
            ORDER BY scope_status
            """
        ).fetchall()

        details = {
            **metadata,
            "step": "load_dim_product",
            "inserted_rows": inserted,
            "unchanged_rows": before,
            "additional_review_outside_scope_csv": extra_review,
            "bidirectional_difference_rows": difference,
            "summary": [
                {
                    "scope_status": status,
                    "products": count,
                    "missing_lookup": missing,
                }
                for status, count, missing in summary
            ],
        }

        # Dữ liệu và log thành công commit cùng nhau.
        conn.execute(
            """
            INSERT INTO audit.reconciliation_result (
                etl_batch_id, dw_load_id,
                source_name, target_name, metric_name,
                source_value, target_value, status, details
            )
            VALUES (
                %s, %s,
                'staging product union + scope v1.3',
                'dw.dim_product', 'product_count',
                %s, %s, 'PASS', %s
            )
            """,
            (
                batch_id, run_id,
                expected_count, actual_count, Jsonb(details),
            ),
        )

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.dim_product',
                'DIM_PRODUCT_LOAD_V1', 'INFO', 'PASS', 0, %s
            )
            """,
            (batch_id, run_id, Jsonb(details)),
        )

    # In kết quả sau khi commit thành công.
    print(f"PASS | Dim_Product | {actual_count:,} sản phẩm")
    print(f"INSERT | {inserted:,} dòng mới")
    print(f"UNCHANGED | {before:,} dòng đã tồn tại")
    print(f"PASS | Đối chiếu hai chiều | {difference} khác biệt")

    for status, count, missing in summary:
        print(
            f"PASS | {status} | {count:,} sản phẩm"
            f" | thiếu lookup={missing:,}"
        )

    if extra_review:
        print(
            f"WARN | {extra_review:,} mã ngoài CSV phân loại"
            " được giữ REVIEW do thiếu lookup"
        )

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

        # Sai run_id hoặc run đã đóng thì chỉ báo lỗi,
        # không thay đổi nhật ký của run đó.
        state = conn.execute(
            "SELECT status FROM audit.dw_load WHERE dw_load_id = %s",
            (args.dw_load_id,),
        ).fetchone()

        require(
            state is not None and state[0] == "RUNNING",
            "DW load phải tồn tại và đang RUNNING.",
        )

        try:
            load_product(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            # Transaction nạp đã rollback trước khi ghi log lỗi.
            mark_failed(
                conn,
                args.dw_load_id,
                "load_dim_product",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()