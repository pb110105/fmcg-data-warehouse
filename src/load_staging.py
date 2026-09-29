import argparse
import gc
import hashlib
import json
import math
import os
from datetime import date, datetime
from decimal import Decimal, getcontext
from numbers import Integral, Real
from pathlib import Path

import pandas as pd
import psycopg
import pyreadr
from dotenv import load_dotenv
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
DATASET = "complete_journey"
PIPELINE_VERSION = "staging-1.0"
LOCK_ID = 23133006

# Đủ độ chính xác để cộng các số thập phân của bộ nguồn hiện tại.
getcontext().prec = 50

FILES = [
    ("products.rda", "stg_products"),
    ("demographics.rda", "stg_demographics"),
    ("campaign_descriptions.rda", "stg_campaign_descriptions"),
    ("campaigns.rda", "stg_campaigns"),
    ("coupons.rda", "stg_coupons"),
    ("coupon_redemptions.rda", "stg_coupon_redemptions"),
    ("transactions.rds", "stg_transactions"),
    ("promotions.rds", "stg_promotions"),
]

METADATA = {
    "staging_row_id",
    "etl_batch_id",
    "source_file_name",
    "source_object_name",
    "source_row_number",
    "loaded_at",
}


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def connect_db():
    load_dotenv(ROOT / ".env")

    required = [
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
    ]
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(f"Thiếu cấu hình .env: {', '.join(missing)}")

    return psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        port=int(os.getenv("POSTGRES_PORT", "5434")),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        connect_timeout=10,
        autocommit=True,
        application_name="fmcg_load_staging",
    )


def get_columns(conn, table):
    rows = conn.execute(
        """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'staging'
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (table,),
    ).fetchall()

    if not rows:
        raise ValueError(f"Không tìm thấy staging.{table}")

    return [(name, dtype) for name, dtype in rows if name not in METADATA]


def convert_value(value, dtype):
    if pd.isna(value):
        return None

    if dtype == "text":
        if isinstance(value, str):
            return value

        # R có thể lưu mã định danh dưới dạng số.
        if isinstance(value, Integral):
            return str(int(value))

        if isinstance(value, Real):
            number = float(value)
            if not math.isfinite(number):
                raise ValueError("Mã số không hữu hạn")
            if not number.is_integer():
                raise ValueError("Mã định danh dạng số có phần thập phân")
            if abs(number) > 2**53:
                raise ValueError("Mã dạng float vượt giới hạn nguyên an toàn")
            return str(int(number))

        raise TypeError(f"Không hỗ trợ chuyển {type(value).__name__} sang TEXT")

    if dtype in {"numeric", "integer"}:
        number = Decimal(str(value))
        if not number.is_finite():
            raise ValueError("Giá trị số không hữu hạn")

        if dtype == "integer":
            if number != number.to_integral_value():
                raise ValueError("Cột INTEGER có phần thập phân")
            return int(number)

        # Không làm tròn tiền hoặc nhân 100 tại Staging.
        return number

    if dtype == "date":
        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        if not isinstance(value, (str, datetime, pd.Timestamp)):
            raise TypeError("DATE phải là ngày hoặc chuỗi ngày")

        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is not None:
            raise ValueError("DATE không được chứa múi giờ")
        if timestamp != timestamp.normalize():
            raise ValueError("Không tự bỏ phần giờ của cột DATE")
        return timestamp.date()

    if dtype == "timestamp with time zone":
        timestamp = pd.Timestamp(value)
        if timestamp.tzinfo is None:
            raise ValueError("Timestamp chưa có múi giờ")

        # PostgreSQL giữ độ chính xác đến microsecond.
        if timestamp.nanosecond != 0:
            raise ValueError("Timestamp có độ chính xác dưới microsecond")

        return timestamp.tz_convert("UTC").to_pydatetime()

    raise TypeError(f"Chưa hỗ trợ kiểu đích: {dtype}")


def timestamp_microseconds(value):
    epoch = datetime(1970, 1, 1, tzinfo=value.tzinfo)
    delta = value - epoch
    return (
        delta.days * 86_400_000_000
        + delta.seconds * 1_000_000
        + delta.microseconds
    )


def write_reconciliation(conn, batch_id, filename, table, checks):
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO audit.reconciliation_result (
                etl_batch_id,
                source_name,
                target_name,
                metric_name,
                source_value,
                target_value,
                status
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            [
                (
                    batch_id,
                    filename,
                    f"staging.{table}",
                    metric,
                    source,
                    target,
                    "PASS" if source == target else "FAIL",
                )
                for metric, source, target in checks
            ],
        )


def load_file(conn, batch_id, folder, filename, table, expected_hash):
    path = folder / filename
    checks = []
    row_number = 0

    conn.execute(
        """
        INSERT INTO audit.etl_file_load (
            etl_batch_id, source_file_name,
            source_file_sha256, target_table
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (etl_batch_id, source_file_name)
        DO UPDATE SET status = 'RUNNING', error_message = NULL
        """,
        (batch_id, filename, expected_hash, f"staging.{table}"),
    )

    try:
        print(f"\nREAD | {filename}", flush=True)

        # Yêu cầu pyreadr trả timestamp theo UTC,
        # bảo toàn thời điểm tuyệt đối của POSIXct.
        result = pyreadr.read_r(str(path), timezone="UTC")

        if len(result) != 1:
            raise ValueError(
                f"File phải có đúng một bảng; tìm thấy {len(result)} đối tượng"
            )

        object_name, frame = next(iter(result.items()))
        del result

        if not isinstance(frame, pd.DataFrame):
            raise TypeError("Đối tượng nguồn không phải DataFrame")

        if sha256_file(path) != expected_hash:
            raise ValueError("File nguồn đã thay đổi trong quá trình đọc")

        columns = get_columns(conn, table)
        names = [name for name, _ in columns]

        if (
            frame.columns.duplicated().any()
            or set(frame.columns) != set(names)
        ):
            raise ValueError(
                f"Cột nguồn không khớp DDL.\n"
                f"Nguồn: {list(frame.columns)}\n"
                f"Đích: {names}"
            )

        # Không tạo bản sao toàn bộ DataFrame chỉ để đổi thứ tự cột.
        positions = [frame.columns.get_loc(name) for name in names]
        null_counts = [0] * len(columns)
        sums = {
            name: Decimal(0)
            for name, dtype in columns
            if dtype in {"numeric", "integer"}
        }
        timestamp_sum = 0
        source_rows = len(frame)

        timezone = (
            "America/New_York" if filename == "transactions.rds" else None
        )

        conn.execute(
            """
            UPDATE audit.etl_file_load
            SET source_object_name = %s,
                source_row_count = %s,
                source_timezone = %s
            WHERE etl_batch_id = %s AND source_file_name = %s
            """,
            (object_name, source_rows, timezone, batch_id, filename),
        )

        target = sql.Identifier("staging", table)
        copy_columns = names + [
            "etl_batch_id",
            "source_file_name",
            "source_object_name",
            "source_row_number",
        ]

        copy_query = sql.SQL("COPY {} ({}) FROM STDIN").format(
            target,
            sql.SQL(", ").join(map(sql.Identifier, copy_columns)),
        )

        # Xóa và nạp lại bảng chưa hoàn tất trong cùng batch.
        # Nếu xảy ra lỗi, toàn bộ transaction của bảng rollback.
        with conn.transaction():
            conn.execute(
                sql.SQL("DELETE FROM {} WHERE etl_batch_id = %s").format(target),
                (batch_id,),
            )
            conn.execute(
                """
                DELETE FROM audit.reconciliation_result
                WHERE etl_batch_id = %s AND target_name = %s
                """,
                (batch_id, f"staging.{table}"),
            )

            with conn.cursor() as cur:
                with cur.copy(copy_query) as copy:
                    for row_number, raw in enumerate(
                        frame.itertuples(index=False, name=None), start=1
                    ):
                        values = []

                        for index, ((name, dtype), position) in enumerate(
                            zip(columns, positions)
                        ):
                            try:
                                value = convert_value(raw[position], dtype)
                            except Exception as exc:
                                raise ValueError(
                                    f"{filename}, dòng {row_number}, "
                                    f"cột {name}: {exc}"
                                ) from exc

                            values.append(value)

                            if value is None:
                                null_counts[index] += 1
                            elif name in sums:
                                sums[name] += value
                            elif dtype == "timestamp with time zone":
                                timestamp_sum += timestamp_microseconds(value)

                        copy.write_row(
                            values
                            + [batch_id, filename, object_name, row_number]
                        )

                        if row_number % 1_000_000 == 0:
                            print(
                                f"COPY | {filename} | "
                                f"{row_number:,}/{source_rows:,}",
                                flush=True,
                            )

            # Đối soát bằng một truy vấn tổng hợp cho mỗi bảng.
            expressions = [sql.SQL("COUNT(*)")]
            source_metrics = [("row_count", source_rows)]

            for index, (name, dtype) in enumerate(columns):
                column = sql.Identifier(name)

                expressions.append(
                    sql.SQL("COUNT(*) FILTER (WHERE {} IS NULL)").format(column)
                )
                source_metrics.append((f"null:{name}", null_counts[index]))

                if name in sums:
                    expressions.append(
                        sql.SQL("COALESCE(SUM({}), 0)").format(column)
                    )
                    source_metrics.append((f"sum:{name}", sums[name]))

                if dtype == "timestamp with time zone":
                    expressions.append(
                        sql.SQL(
                            "COALESCE(SUM(EXTRACT(EPOCH FROM {})"
                            " * 1000000), 0)"
                        ).format(column)
                    )
                    source_metrics.append(
                        (f"epoch_microseconds:{name}", timestamp_sum)
                    )

            actual = conn.execute(
                sql.SQL(
                    "SELECT {} FROM {} WHERE etl_batch_id = %s"
                ).format(sql.SQL(", ").join(expressions), target),
                (batch_id,),
            ).fetchone()

            checks = [
                (metric, source_value, target_value)
                for (metric, source_value), target_value
                in zip(source_metrics, actual)
            ]

            failures = [
                metric
                for metric, source_value, target_value in checks
                if source_value != target_value
            ]

            if failures:
                raise ValueError(f"Đối soát không khớp: {failures}")

            write_reconciliation(
                conn, batch_id, filename, table, checks
            )

            conn.execute(
                """
                UPDATE audit.etl_file_load
                SET loaded_row_count = %s,
                    status = 'SUCCESS',
                    error_message = NULL
                WHERE etl_batch_id = %s AND source_file_name = %s
                """,
                (actual[0], batch_id, filename),
            )

        print(
            f"PASS | {filename} | {source_rows:,} dòng | "
            f"{len(checks)} kiểm tra đối soát",
            flush=True,
        )

        del frame
        gc.collect()

    except BaseException as exc:
        # Ghi audit ngoài transaction đã rollback.
        with conn.transaction():
            conn.execute(
                """
                DELETE FROM audit.reconciliation_result
                WHERE etl_batch_id = %s AND target_name = %s
                """,
                (batch_id, f"staging.{table}"),
            )

            if checks:
                write_reconciliation(
                    conn, batch_id, filename, table, checks
                )

            conn.execute(
                """
                UPDATE audit.etl_file_load
                SET status = 'FAILED',
                    error_message = %s
                WHERE etl_batch_id = %s AND source_file_name = %s
                """,
                (
                    f"{type(exc).__name__}; dòng đang xử lý "
                    f"{row_number}: {exc}"[:4000],
                    batch_id,
                    filename,
                ),
            )
        raise


def run(conn, folder):
    print("Đang kiểm tra file và tính SHA-256...", flush=True)

    hashes = {}
    for filename, _ in FILES:
        path = folder / filename
        if not path.is_file():
            raise FileNotFoundError(f"Thiếu file: {path}")
        hashes[filename] = sha256_file(path)

    manifest = hashlib.sha256(
        json.dumps(hashes, sort_keys=True).encode("utf-8")
    ).hexdigest()

    # Khóa phiên: ngăn hai chương trình nạp đồng thời.
    locked = conn.execute(
        "SELECT pg_try_advisory_lock(%s)", (LOCK_ID,)
    ).fetchone()[0]

    if not locked:
        raise RuntimeError("Đang có một chương trình nạp Staging khác chạy")

    # Khóa tự giải phóng khi đóng kết nối.
    existing = conn.execute(
        """
        SELECT etl_batch_id, status
        FROM audit.etl_batch
        WHERE dataset_name = %s
          AND source_manifest_hash = %s
          AND pipeline_version = %s
        ORDER BY
            CASE status
                WHEN 'SUCCESS' THEN 0
                WHEN 'RUNNING' THEN 1
                ELSE 2
            END,
            etl_batch_id DESC
        LIMIT 1
        """,
        (DATASET, manifest, PIPELINE_VERSION),
    ).fetchone()

    if existing and existing[1] == "SUCCESS":
        print(
            f"SKIP | Batch {existing[0]} đã SUCCESS; "
            "không nạp thêm dữ liệu."
        )
        return

    if existing:
        batch_id = existing[0]
        conn.execute(
            """
            UPDATE audit.etl_batch
            SET status = 'RUNNING',
                finished_at = NULL,
                error_message = NULL
            WHERE etl_batch_id = %s
            """,
            (batch_id,),
        )
        print(f"RESUME | Batch {batch_id}", flush=True)
    else:
        batch_id = conn.execute(
            """
            INSERT INTO audit.etl_batch (
                dataset_name, source_manifest_hash, pipeline_version
            )
            VALUES (%s, %s, %s)
            RETURNING etl_batch_id
            """,
            (DATASET, manifest, PIPELINE_VERSION),
        ).fetchone()[0]
        print(f"START | Batch {batch_id}", flush=True)

    try:
        for filename, table in FILES:
            previous = conn.execute(
                """
                SELECT status
                FROM audit.etl_file_load
                WHERE etl_batch_id = %s AND source_file_name = %s
                """,
                (batch_id, filename),
            ).fetchone()

            if previous and previous[0] == "SUCCESS":
                print(f"SKIP FILE | {filename} đã SUCCESS", flush=True)
                continue

            load_file(
                conn, batch_id, folder, filename, table, hashes[filename]
            )

        completed = conn.execute(
            """
            SELECT COUNT(*)
            FROM audit.etl_file_load
            WHERE etl_batch_id = %s AND status = 'SUCCESS'
            """,
            (batch_id,),
        ).fetchone()[0]

        if completed != len(FILES):
            raise RuntimeError("Chưa đủ tám file SUCCESS")

        conn.execute(
            """
            UPDATE audit.etl_batch
            SET status = 'SUCCESS',
                finished_at = clock_timestamp(),
                error_message = NULL
            WHERE etl_batch_id = %s
            """,
            (batch_id,),
        )
        print(f"\nSUCCESS | Batch {batch_id} | Đủ tám bảng Staging")

    except BaseException as exc:
        conn.execute(
            """
            UPDATE audit.etl_batch
            SET status = 'FAILED',
                finished_at = clock_timestamp(),
                error_message = %s
            WHERE etl_batch_id = %s
            """,
            (f"{type(exc).__name__}: {exc}"[:4000], batch_id),
        )
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data",
        type=Path,
        default=ROOT / "data" / "raw" / "complete_journey",
    )
    args = parser.parse_args()

    with connect_db() as conn:
        conn.execute("SET TIME ZONE 'UTC'")
        database = conn.execute(
            "SELECT current_database()"
        ).fetchone()[0]
        print(f"CONNECTED | {database}", flush=True)
        run(conn, args.data.resolve())


if __name__ == "__main__":
    main()