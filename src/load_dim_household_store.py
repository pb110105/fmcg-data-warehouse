import argparse
from pathlib import Path

from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs, require
from check_dw_quality import create_normalized_views
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION


HOUSEHOLD_COLUMNS = [
    "household_id",
    "age",
    "income",
    "home_ownership",
    "marital_status",
    "household_size",
    "household_comp",
    "kids_count",
    "demographics_available_flag",
    "etl_batch_id",
]

STORE_COLUMNS = ["store_id", "etl_batch_id"]


def load_dimension(
    conn, batch_id, run_id, table, expected_table, key, columns
):
    # Hỗ trợ khóa đơn và khóa ghép.
    keys = [key] if isinstance(key, str) else list(key)
    key_list = ", ".join(keys)

    join_condition = " AND ".join(
        f"d.{column} = e.{column}" for column in keys
    )
    order_by = ", ".join(f"e.{column}" for column in keys)

    column_list = ", ".join(columns)
    target_values = ", ".join(f"d.{c}" for c in columns)
    expected_values = ", ".join(f"e.{c}" for c in columns)

    conflicts = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM dw.{table} d
        JOIN {expected_table} e USING ({key_list})
        WHERE ROW({target_values})
              IS DISTINCT FROM ROW({expected_values})
        """
    ).fetchone()[0]

    require(
        conflicts == 0,
        f"{table}: có {conflicts} dòng khác dữ liệu dự kiến; dừng nạp.",
    )

    extras = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM dw.{table} d
        WHERE NOT EXISTS (
            SELECT 1 FROM {expected_table} e
            WHERE {join_condition}
        )
        """
    ).fetchone()[0]

    require(
        extras == 0,
        f"{table}: có mã ngoài bộ nguồn hiện tại.",
    )

    before = conn.execute(
        f"SELECT COUNT(*) FROM dw.{table}"
    ).fetchone()[0]

    inserted = conn.execute(
        f"""
        INSERT INTO dw.{table} ({column_list})
        SELECT {expected_values}
        FROM {expected_table} e
        WHERE NOT EXISTS (
            SELECT 1 FROM dw.{table} d
            WHERE {join_condition}
        )
        ORDER BY {order_by}
        """
    ).rowcount

    difference = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            (
                SELECT {column_list} FROM {expected_table}
                EXCEPT
                SELECT {column_list} FROM dw.{table}
            )
            UNION ALL
            (
                SELECT {column_list} FROM dw.{table}
                EXCEPT
                SELECT {column_list} FROM {expected_table}
            )
        ) differences
        """
    ).fetchone()[0]

    expected_count = conn.execute(
        f"SELECT COUNT(*) FROM {expected_table}"
    ).fetchone()[0]

    actual_count = conn.execute(
        f"SELECT COUNT(*) FROM dw.{table}"
    ).fetchone()[0]

    require(
        difference == 0
        and actual_count == expected_count
        and actual_count == before + inserted,
        f"{table}: đối soát không khớp.",
    )

    details = {
        "step": f"load_{table}",
        "inserted_rows": inserted,
        "unchanged_rows": before,
        "bidirectional_difference_rows": difference,
    }

    conn.execute(
        """
        INSERT INTO audit.reconciliation_result (
            etl_batch_id, dw_load_id,
            source_name, target_name, metric_name,
            source_value, target_value, status, details
        )
        VALUES (%s, %s, %s, %s, 'row_count', %s, %s, 'PASS', %s)
        """,
        (
            batch_id, run_id,
            expected_table, f"dw.{table}",
            expected_count, actual_count, Jsonb(details),
        ),
    )

    conn.execute(
        """
        INSERT INTO audit.data_quality_result (
            etl_batch_id, dw_load_id, table_name,
            rule_code, severity, status, affected_rows, details
        )
        VALUES (%s, %s, %s, %s, 'INFO', 'PASS', 0, %s)
        """,
        (
            batch_id, run_id, f"dw.{table}",
            f"{table.upper()}_LOAD_V1", Jsonb(details),
        ),
    )

    return table, actual_count, inserted, before

def load_household_store(conn, run_id, scope_dir, raw_dir):
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

        # Gate dành cho phiên bản DQ_V1 hiện tại: 57 quy tắc.
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

        # Thuộc tính mô tả đã được trim và đổi chuỗi rỗng thành NULL.
        conn.execute(
            """
            CREATE TEMP TABLE household_lookup ON COMMIT DROP AS
            SELECT DISTINCT
                   household_id, age, income,
                   home_ownership, marital_status,
                   household_size, household_comp, kids_count
            FROM q_demographics
            """
        )

        conflicts = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT household_id
                FROM household_lookup
                GROUP BY household_id
                HAVING COUNT(*) > 1
            ) x
            """
        ).fetchone()[0]

        require(
            conflicts == 0,
            "Nhân khẩu học có thuộc tính mâu thuẫn trên cùng mã hộ.",
        )

        conn.execute(
            """
            ALTER TABLE household_lookup
            ADD PRIMARY KEY (household_id)
            """
        )

        conn.execute(
            """
            CREATE TEMP TABLE household_ids ON COMMIT DROP AS
            SELECT household_id FROM q_demographics
            UNION
            SELECT household_id FROM q_transactions
            UNION
            SELECT household_id FROM q_campaigns
            UNION
            SELECT household_id FROM q_coupon_redemptions
            """
        )

        conn.execute(
            """
            CREATE TEMP TABLE store_ids ON COMMIT DROP AS
            SELECT store_id FROM q_transactions
            UNION
            SELECT store_id FROM q_promotions
            """
        )

        for table, key in (
            ("household_ids", "household_id"),
            ("store_ids", "store_id"),
        ):
            invalid = conn.execute(
                f"""
                SELECT COUNT(*)
                FROM {table}
                WHERE {key} IS NULL OR BTRIM({key}) = ''
                """
            ).fetchone()[0]

            require(invalid == 0, f"{table}: có mã NULL hoặc rỗng.")

            conn.execute(
                f"ALTER TABLE {table} ADD PRIMARY KEY ({key})"
            )

        conn.execute(
            """
            CREATE TEMP TABLE expected_household ON COMMIT DROP AS
            SELECT
                i.household_id,
                d.age,
                d.income,
                d.home_ownership,
                d.marital_status,
                d.household_size,
                d.household_comp,
                d.kids_count,
                (d.household_id IS NOT NULL)
                    AS demographics_available_flag,
                %s::bigint AS etl_batch_id
            FROM household_ids i
            LEFT JOIN household_lookup d USING (household_id)
            """,
            (batch_id,),
        )

        conn.execute(
            """
            ALTER TABLE expected_household
            ADD PRIMARY KEY (household_id)
            """
        )

        conn.execute(
            """
            CREATE TEMP TABLE expected_store ON COMMIT DROP AS
            SELECT store_id, %s::bigint AS etl_batch_id
            FROM store_ids
            """,
            (batch_id,),
        )

        conn.execute(
            """
            ALTER TABLE expected_store
            ADD PRIMARY KEY (store_id)
            """
        )

        results = [
            load_dimension(
                conn, batch_id, run_id,
                "dim_household", "expected_household",
                "household_id", HOUSEHOLD_COLUMNS,
            ),
            load_dimension(
                conn, batch_id, run_id,
                "dim_store", "expected_store",
                "store_id", STORE_COLUMNS,
            ),
        ]

        available, missing = conn.execute(
            """
            SELECT
                COUNT(*) FILTER (WHERE demographics_available_flag),
                COUNT(*) FILTER (WHERE NOT demographics_available_flag)
            FROM dw.dim_household
            """
        ).fetchone()

        # Cảnh báo được lưu cả khi số hộ thiếu bằng 0.
        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id, dw_load_id, table_name,
                rule_code, severity, status, affected_rows, details
            )
            VALUES (
                %s, %s, 'dw.dim_household',
                'DIM_HOUSEHOLD_MISSING_DEMOGRAPHICS_V1',
                'WARNING', %s, %s, %s
            )
            """,
            (
                batch_id, run_id,
                "FAIL" if missing else "PASS",
                missing,
                Jsonb({
                    "count_unit": "distinct_households",
                    "action": "Giữ hộ; thuộc tính NULL; cờ FALSE",
                    "demographics_available": available,
                }),
            ),
        )

    # Hai Dimension và log được commit trong cùng transaction.
    for table, total, inserted, unchanged in results:
        print(f"PASS | {table} | {total:,} dòng")
        print(f"INSERT | {inserted:,} dòng mới")
        print(f"UNCHANGED | {unchanged:,} dòng đã tồn tại")
        print("PASS | Đối chiếu hai chiều | 0 khác biệt")

    print(f"INFO | Hộ có bản ghi nhân khẩu học | {available:,}")
    print(f"INFO | Hộ thiếu bản ghi nhân khẩu học | {missing:,}")
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
            load_household_store(
                conn,
                args.dw_load_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_dim_household_store",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()