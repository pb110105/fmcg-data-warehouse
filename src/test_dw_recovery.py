import argparse

from psycopg.types.json import Jsonb

from load_staging import connect_db
from check_dw_inputs import require
from dw_run import acquire_lock
from load_dim_household_store import load_dimension


DIMENSIONS = {
    "dim_date": ("date_key", ["full_date"]),
    "dim_week": (
        "week_key",
        ["source_calendar_id", "source_week"],
    ),
    "dim_product": ("product_key", ["product_id"]),
    "dim_household": ("household_key", ["household_id"]),
    "dim_store": ("store_key", ["store_id"]),
    "dim_campaign": ("campaign_key", ["campaign_id"]),
    "dim_coupon": (
        "coupon_key",
        ["campaign_id", "coupon_upc"],
    ),
}

COUPON_COLUMNS = [
    "household_key",
    "coupon_key",
    "campaign_key",
    "redemption_date_key",
    "redemption_record_count",
    "etl_batch_id",
]

COUPON_KEYS = [
    "household_key",
    "coupon_key",
    "campaign_key",
    "redemption_date_key",
]


class SimulatedFailure(Exception):
    pass


class RollbackSuccessfulTrial(Exception):
    pass


def scalar(conn, query, params=None):
    return conn.execute(query, params).fetchone()[0]


def difference_count(conn, table, snapshot):
    # Tên bảng do chương trình quy định.
    return scalar(
        conn,
        f"""
        SELECT COUNT(*)
        FROM (
            (
                SELECT * FROM dw.{table}
                EXCEPT ALL
                SELECT * FROM {snapshot}
            )
            UNION ALL
            (
                SELECT * FROM {snapshot}
                EXCEPT ALL
                SELECT * FROM dw.{table}
            )
        ) differences
        """,
    )


def run_test(conn, run_id):
    with conn.transaction():
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )

        run = conn.execute(
            """
            SELECT source_batch_id, status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            FOR UPDATE
            """,
            (run_id,),
        ).fetchone()

        require(
            run is not None and run[1] == "RUNNING",
            "DW load phải tồn tại và đang RUNNING.",
        )
        batch_id = run[0]

        latest_verify = conn.execute(
            """
            SELECT status
            FROM audit.data_quality_result
            WHERE dw_load_id = %s
              AND etl_batch_id = %s
              AND rule_code = 'DW_VERIFY_V1'
            ORDER BY checked_at DESC, dq_result_id DESC
            LIMIT 1
            """,
            (run_id, batch_id),
        ).fetchone()

        require(
            latest_verify is not None
            and latest_verify[0] == "PASS",
            "Cần có kết quả verify PASS trước khi thử phục hồi.",
        )

        # Ngăn ghi đồng thời vào các bảng đang thử nghiệm.
        # Truy vấn SELECT thông thường vẫn có thể chạy.
        tables = list(DIMENSIONS) + ["fact_coupon_redemption"]
        table_list = ", ".join(f"dw.{name}" for name in tables)

        conn.execute(
            f"LOCK TABLE {table_list} "
            "IN SHARE ROW EXCLUSIVE MODE"
        )

        print(
            "\n=== 1. CHẠY LẠI CƠ CHẾ NẠP DIMENSION ===",
            flush=True,
        )

        for table, (surrogate_key, business_keys) in DIMENSIONS.items():
            snapshot = f"test_snapshot_{table}"
            expected = f"test_expected_{table}"

            conn.execute(
                f"""
                CREATE TEMP TABLE {snapshot}
                ON COMMIT DROP AS
                SELECT * FROM dw.{table}
                """
            )

            # Không đưa khóa identity và loaded_at vào INSERT.
            # Dim_Date dùng date_key tự xác định nên vẫn giữ date_key.
            columns = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'dw'
                      AND table_name = %s
                      AND is_identity = 'NO'
                      AND is_generated = 'NEVER'
                      AND column_name <> 'loaded_at'
                    ORDER BY ordinal_position
                    """,
                    (table,),
                ).fetchall()
            ]

            column_list = ", ".join(columns)

            conn.execute(
                f"""
                CREATE TEMP TABLE {expected}
                ON COMMIT DROP AS
                SELECT {column_list}
                FROM {snapshot}
                """
            )

            # Rollback cả log do helper sinh ra:
            # đây là phép thử, không phải một lần nạp nghiệp vụ mới.
            try:
                with conn.transaction():
                    result = load_dimension(
                        conn,
                        batch_id,
                        run_id,
                        table,
                        expected,
                        business_keys,
                        columns,
                    )

                    require(
                        result[2] == 0,
                        f"{table}: chạy lại đã chèn thêm dữ liệu.",
                    )

                    require(
                        difference_count(conn, table, snapshot) == 0,
                        f"{table}: dữ liệu hoặc khóa đã thay đổi.",
                    )

                    raise RollbackSuccessfulTrial()

            except RollbackSuccessfulTrial:
                pass

            require(
                difference_count(conn, table, snapshot) == 0,
                f"{table}: trạng thái sau phép thử không khớp.",
            )

            print(
                f"PASS | {table} | INSERT=0 | "
                f"giữ nguyên {surrogate_key} và toàn bộ dòng",
                flush=True,
            )

        print(
            "\n=== 2. GIẢ LẬP LỖI SAU KHI NẠP ===",
            flush=True,
        )

        conn.execute(
            """
            CREATE TEMP TABLE test_redemption_snapshot
            ON COMMIT DROP AS
            SELECT * FROM dw.fact_coupon_redemption
            """
        )

        column_list = ", ".join(COUPON_COLUMNS)

        conn.execute(
            f"""
            CREATE TEMP TABLE test_expected_redemption
            ON COMMIT DROP AS
            SELECT {column_list}
            FROM test_redemption_snapshot
            """
        )

        victim_key = scalar(
            conn,
            """
            SELECT MIN(redemption_key)
            FROM test_redemption_snapshot
            """,
        )
        require(victim_key is not None, "Bảng redemption đang rỗng.")

        def restore_one_row():
            deleted = conn.execute(
                """
                DELETE FROM dw.fact_coupon_redemption
                WHERE redemption_key = %s
                """,
                (victim_key,),
            ).rowcount

            require(deleted == 1, "Không chọn được đúng một dòng thử.")

            result = load_dimension(
                conn,
                batch_id,
                run_id,
                "fact_coupon_redemption",
                "test_expected_redemption",
                COUPON_KEYS,
                COUPON_COLUMNS,
            )

            require(
                result[2] == 1,
                "Phục hồi phải chèn đúng một dòng bị thiếu.",
            )
            return result

        try:
            # Savepoint: tất cả thay đổi bên trong sẽ rollback khi lỗi.
            with conn.transaction():
                restore_one_row()
                raise SimulatedFailure(
                    "Lỗi giả lập sau INSERT, trước commit."
                )

        except SimulatedFailure:
            print(
                "PASS | Đã kích hoạt lỗi giả lập và rollback",
                flush=True,
            )

        require(
            difference_count(
                conn,
                "fact_coupon_redemption",
                "test_redemption_snapshot",
            ) == 0,
            "Rollback chưa trả bảng về đúng trạng thái ban đầu.",
        )

        print(
            "PASS | Sau lỗi: toàn bộ dòng và khóa Fact giữ nguyên",
            flush=True,
        )

        print(
            "\n=== 3. THỬ PHỤC HỒI VÀ CHẠY LẠI ===",
            flush=True,
        )

        try:
            with conn.transaction():
                restore_one_row()

                print(
                    "PASS | Thử lại: phục hồi đúng một dòng",
                    flush=True,
                )

                result = load_dimension(
                    conn,
                    batch_id,
                    run_id,
                    "fact_coupon_redemption",
                    "test_expected_redemption",
                    COUPON_KEYS,
                    COUPON_COLUMNS,
                )

                require(
                    result[2] == 0,
                    "Chạy lại sau phục hồi đã chèn trùng.",
                )

                print(
                    "PASS | Sau phục hồi: chạy lại INSERT=0",
                    flush=True,
                )

                # Phép thử thành công nhưng không công bố thay đổi thử.
                raise RollbackSuccessfulTrial()

        except RollbackSuccessfulTrial:
            pass

        require(
            difference_count(
                conn,
                "fact_coupon_redemption",
                "test_redemption_snapshot",
            ) == 0,
            "Trạng thái cuối khác dữ liệu trước phép thử.",
        )

        print(
            "PASS | Kết thúc thử: DW trở về đúng trạng thái ban đầu",
            flush=True,
        )

        # Chỉ lưu kết quả bài kiểm tra, không giữ log nạp giả lập.
        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw',
                'DW_RECOVERY_TEST_V1',
                'INFO', 'PASS', 0, %s
            )
            """,
            (
                batch_id,
                run_id,
                Jsonb({
                    "dimension_tables_checked": 7,
                    "dimension_keys_unchanged": True,
                    "loader": "load_dimension",
                    "recovery_table": "fact_coupon_redemption",
                    "simulated_failure": "after_insert_before_commit",
                    "rollback_restored_original_rows": True,
                    "retry_inserted_rows": 1,
                    "retry_second_inserted_rows": 0,
                    "test_changes_rolled_back": True,
                    "scope": (
                        "Shared loader idempotency and transaction rollback; "
                        "not process-kill or Docker-crash recovery"
                    ),
                }),
            ),
        )

    print("\nDW RECOVERY TEST: PASS")
    print(f"dw_load_id={run_id} vẫn RUNNING.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dw-load-id", type=int, required=True)
    args = parser.parse_args()

    with connect_db() as conn:
        acquire_lock(conn)
        run_test(conn, args.dw_load_id)


if __name__ == "__main__":
    main()