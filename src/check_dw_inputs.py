import argparse
import hashlib
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

from load_staging import ROOT, FILES, connect_db, sha256_file


RULE_VERSION = "1.3-cosmetics-and-exclusions"

# Mốc dành cho bộ nguồn và phân loại v1.3 hiện tại.
EXPECTED = {
    "IN_SCOPE": (1271042, Decimal("3419948.46")),
    "OUT_OF_SCOPE": (20691, Decimal("395944.98")),
    "REVIEW": (177574, Decimal("780146.14")),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_inputs(conn, batch_id, scope_dir, raw_dir):
    validation_path = scope_dir / "validation.json"
    scope_path = scope_dir / "product_scope.csv"

    require(validation_path.is_file(), f"Thiếu {validation_path}")
    require(scope_path.is_file(), f"Thiếu {scope_path}")

    # Đọc đúng các byte dùng để tính hash.
    scope_bytes = scope_path.read_bytes()
    scope_hash = hashlib.sha256(scope_bytes).hexdigest()

    validation = json.loads(
        validation_path.read_text(encoding="utf-8-sig")
    )

    require(
        validation.get("rule_version") == RULE_VERSION,
        "validation.json không phải phiên bản v1.3 đã chốt",
    )
    require(
        validation.get("row_reconciliation") == "PASS"
        and validation.get("sales_reconciliation") == "PASS",
        "validation.json chưa đạt đối soát",
    )

    batch = conn.execute(
        """
        SELECT dataset_name, status, source_manifest_hash
        FROM audit.etl_batch
        WHERE etl_batch_id = %s
        """,
        (batch_id,),
    ).fetchone()

    require(batch is not None, f"Không tìm thấy Batch {batch_id}")
    require(
        batch[0] == "complete_journey" and batch[1] == "SUCCESS",
        "Batch không phải Complete Journey SUCCESS",
    )
    print(f"PASS | Batch {batch_id} | SUCCESS")

    file_rows = conn.execute(
        """
        SELECT source_file_name, source_file_sha256,
               source_row_count, loaded_row_count,
               status, target_table
        FROM audit.etl_file_load
        WHERE etl_batch_id = %s
        """,
        (batch_id,),
    ).fetchall()

    files = {row[0]: row[1:] for row in file_rows}
    expected_files = dict(FILES)

    require(
        set(files) == set(expected_files),
        "Danh sách file trong batch không khớp tám file nguồn",
    )

    for filename, table in FILES:
        digest, source_rows, loaded_rows, status, target = files[filename]
        require(
            status == "SUCCESS"
            and source_rows is not None
            and source_rows == loaded_rows
            and target == f"staging.{table}",
            f"Audit chưa hợp lệ: {filename}",
        )

    audit_hashes = {
        filename: files[filename][0]
        for filename in expected_files
    }

    manifest_hash = hashlib.sha256(
        json.dumps(audit_hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()

    require(
        manifest_hash == batch[2],
        "Manifest batch không khớp hash của tám file trong audit",
    )
    print("PASS | Tám file và manifest trong audit")

    # Đối chiếu hai file dùng để tạo kết quả phân loại.
    for filename in ("products.rda", "transactions.rds"):
        audit_hash = audit_hashes[filename]
        validation_hash = validation.get("sources", {}).get(filename)

        require(
            validation_hash == audit_hash,
            f"Hash {filename}: validation.json khác batch Staging",
        )

        raw_path = raw_dir / filename
        require(raw_path.is_file(), f"Thiếu {raw_path}")
        require(
            sha256_file(raw_path) == audit_hash,
            f"File Raw hiện tại đã thay đổi: {filename}",
        )
        print(f"PASS | Hash nguồn | {filename}")

    # Giữ mã định danh dạng chuỗi; không tự đổi mã hoặc trim.
    from io import BytesIO

    scope = pd.read_csv(
        BytesIO(scope_bytes),
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    required_columns = {
        "product_id",
        "scope_status",
        "scope_reason",
        "scope_rule_version",
    }
    require(
        required_columns.issubset(scope.columns),
        f"CSV thiếu cột: {required_columns - set(scope.columns)}",
    )
    require(
        scope["product_id"].str.strip().ne("").all(),
        "CSV có product_id rỗng",
    )
    require(
        not scope["product_id"].duplicated().any(),
        "CSV có product_id trùng",
    )
    require(
        scope["scope_status"].isin(EXPECTED).all(),
        "CSV có scope_status ngoài miền cho phép",
    )
    require(
        scope["scope_rule_version"].eq(RULE_VERSION).all(),
        "CSV có scope_rule_version không khớp v1.3",
    )
    require(
        scope["scope_reason"].str.strip().ne("").all(),
        "CSV có phân loại thiếu lý do",
    )
    print(f"PASS | Cấu trúc phân loại | {len(scope):,} sản phẩm")

    # Chỉ tạo bảng tạm trong phiên để đối chiếu với Staging.
    conn.execute(
        """
        CREATE TEMP TABLE input_scope_check (
            product_id TEXT PRIMARY KEY,
            scope_status TEXT NOT NULL
        ) ON COMMIT DROP
        """
    )

    with conn.cursor() as cur:
        with cur.copy(
            "COPY input_scope_check "
            "(product_id, scope_status) FROM STDIN"
        ) as copy:
            for row in scope[
                ["product_id", "scope_status"]
            ].itertuples(index=False, name=None):
                copy.write_row(row)

    source_stats = conn.execute(
        """
        SELECT
            COUNT(*),
            COALESCE(SUM(ROUND(sales_value * 100)), 0),
            COUNT(*) FILTER (WHERE sales_value IS NULL),
            COUNT(*) FILTER (
                WHERE sales_value IS NOT NULL
                  AND (
                      sales_value::text IN ('NaN', 'Infinity', '-Infinity')
                      OR ABS(
                          sales_value * 100
                          - ROUND(sales_value * 100)
                      ) >= 0.000001
                  )
            )
        FROM staging.stg_transactions
        WHERE etl_batch_id = %s
        """,
        (batch_id,),
    ).fetchone()

    require(
        source_stats[0] == validation.get("source_rows"),
        "Số dòng giao dịch khác validation.json",
    )
    require(
        source_stats[2] == 0,
        "Giao dịch có sales_value NULL",
    )
    require(
        source_stats[3] == 0,
        f"Có {source_stats[3]} dòng tiền không hữu hạn "
        "hoặc lệch đơn vị cent vượt ngưỡng cho phép",
    )
    require(
        source_stats[1] == validation.get("source_sales_cents"),
        f"Tổng sales_value theo cent không khớp: "
        f"Staging={source_stats[1]}, "
        f"validation={validation.get('source_sales_cents')}",
    )

    print(
        f"PASS | Tổng sales_value | "
        f"{source_stats[1]} cent"
    )
        # 1. Đối chiếu số dòng danh mục sản phẩm.
    product_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM staging.stg_products
        WHERE etl_batch_id = %s
        """,
        (batch_id,),
    ).fetchone()[0]

    require(
        product_count == validation.get("lookup_products"),
        "Số dòng products khác validation.json",
    )
    print(f"PASS | Danh mục nguồn | {product_count:,} dòng")

    # 2. CSV phải bao phủ đúng hợp mã products và transactions.
    missing, extra = conn.execute(
        """
        WITH source_ids AS (
            SELECT product_id
            FROM staging.stg_products
            WHERE etl_batch_id = %s

            UNION

            SELECT product_id
            FROM staging.stg_transactions
            WHERE etl_batch_id = %s
        )
        SELECT
            (
                SELECT COUNT(*)
                FROM source_ids s
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM input_scope_check c
                    WHERE c.product_id = s.product_id
                )
            ),
            (
                SELECT COUNT(*)
                FROM input_scope_check c
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM source_ids s
                    WHERE s.product_id = c.product_id
                )
            )
        """,
        (batch_id, batch_id),
    ).fetchone()

    require(
        missing == 0 and extra == 0,
        f"CSV không khớp mã nguồn: thiếu {missing}, thừa {extra}",
    )
    print("PASS | Mã sản phẩm phân loại | Không thiếu, không thừa")

    # 3. Sản phẩm thiếu lookup phải được giữ REVIEW.
    orphan_count, invalid_orphans = conn.execute(
        """
        SELECT
            COUNT(*),
            COUNT(*) FILTER (
                WHERE c.scope_status <> 'REVIEW'
            )
        FROM input_scope_check c
        WHERE NOT EXISTS (
            SELECT 1
            FROM staging.stg_products p
            WHERE p.etl_batch_id = %s
              AND p.product_id = c.product_id
        )
        """,
        (batch_id,),
    ).fetchone()

    require(
        orphan_count == validation.get("missing_lookup_products"),
        "Số sản phẩm thiếu lookup khác validation.json",
    )
    require(
        invalid_orphans == 0,
        "Có sản phẩm thiếu lookup nhưng không được giữ REVIEW",
    )
    print(
        f"PASS | Bao phủ mã sản phẩm | "
        f"{orphan_count} mã thiếu lookup đều REVIEW"
    )
    results = conn.execute(
        """
        SELECT c.scope_status,
               COUNT(*) AS transaction_rows,
               SUM(ROUND(t.sales_value * 100)) / 100 AS sales_value
        FROM staging.stg_transactions t
        JOIN input_scope_check c
          ON c.product_id = t.product_id
        WHERE t.etl_batch_id = %s
        GROUP BY c.scope_status
        ORDER BY c.scope_status
        """,
        (batch_id,),
    ).fetchall()

    actual = {status: (rows, sales) for status, rows, sales in results}
    require(
        actual == EXPECTED,
        f"Kết quả phân loại khác mốc v1.3 đã chốt: {actual}",
    )

    for status, rows, sales in results:
        print(f"PASS | {status} | {rows:,} dòng | sales_value={sales}")

    # Trả metadata để bước sau dùng khi tạo audit.dw_load.
    return {
        "source_batch_id": batch_id,
        "source_manifest_hash": manifest_hash,
        "scope_rule_version": RULE_VERSION,
        "scope_file_sha256": scope_hash,
        "source_calendar_id": "CJ_2017",
        "scope_product_count": len(scope),
        "input_check": "PASS",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-id", type=int, required=True)
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
        with conn.transaction():
            # Các truy vấn đối chiếu nhìn cùng một ảnh chụp dữ liệu.
            conn.execute(
                "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
            )
            metadata = check_inputs(
                conn,
                args.batch_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )

    print("\nDW INPUT CHECK: PASS")
    print(json.dumps(metadata, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()