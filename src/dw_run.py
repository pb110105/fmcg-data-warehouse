import argparse
import json
from pathlib import Path

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from load_staging import ROOT, connect_db
from check_dw_inputs import check_inputs


PIPELINE_VERSION = "dw-1.0"
LOCK_ID = 23133006


def acquire_lock(conn):
    locked = conn.execute(
        "SELECT pg_try_advisory_lock(%s)",
        (LOCK_ID,),
    ).fetchone()[0]

    if not locked:
        raise RuntimeError(
            "Một tác vụ ETL khác đang giữ khóa. Hãy chạy lại sau."
        )


def start_run(conn, batch_id, scope_dir, raw_dir):
    # Khóa được giữ đến khi đóng kết nối.
    acquire_lock(conn)

    with conn.transaction():
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )

        metadata = check_inputs(
            conn,
            batch_id,
            scope_dir,
            raw_dir,
        )

        identity = (
            metadata["source_batch_id"],
            PIPELINE_VERSION,
            metadata["scope_rule_version"],
            metadata["scope_file_sha256"],
            metadata["source_calendar_id"],
        )

        # Chỉ cho phép một lần nạp DW đang mở.
        running = conn.execute(
            """
            SELECT dw_load_id,
                   source_batch_id,
                   pipeline_version,
                   scope_rule_version,
                   scope_file_sha256,
                   source_calendar_id
            FROM audit.dw_load
            WHERE status = 'RUNNING'
            ORDER BY dw_load_id
            """
        ).fetchall()

        if len(running) > 1:
            raise RuntimeError(
                "Có nhiều lần nạp RUNNING; cần kiểm tra nhật ký."
            )

        if running:
            current = running[0]

            if tuple(current[1:]) != identity:
                raise RuntimeError(
                    f"DW load {current[0]} đang mở với đầu vào khác. "
                    "Cần xử lý lần nạp đó trước."
                )

            return current[0], "REUSE", "RUNNING"

        successful = conn.execute(
            """
            SELECT dw_load_id
            FROM audit.dw_load
            WHERE source_batch_id = %s
              AND pipeline_version = %s
              AND scope_rule_version = %s
              AND scope_file_sha256 = %s
              AND source_calendar_id = %s
              AND status = 'SUCCESS'
            ORDER BY dw_load_id DESC
            LIMIT 1
            """,
            identity,
        ).fetchone()

        if successful:
            return successful[0], "SKIP", "SUCCESS"

        dw_load_id = conn.execute(
            """
            INSERT INTO audit.dw_load (
                source_batch_id,
                pipeline_version,
                scope_rule_version,
                scope_file_sha256,
                source_calendar_id,
                status
            )
            VALUES (%s, %s, %s, %s, %s, 'RUNNING')
            RETURNING dw_load_id
            """,
            identity,
        ).fetchone()[0]

        # Lưu kết quả kiểm tra đầu vào cùng lần nạp DW.
        details = {
            **metadata,
            "pipeline_version": PIPELINE_VERSION,
            "step": "initialize",
        }

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id,
                dw_load_id,
                table_name,
                rule_code,
                severity,
                status,
                affected_rows,
                details
            )
            VALUES (
                %s, %s, 'DW_INPUTS',
                'DW_INPUT_CHECK_V1',
                'INFO', 'PASS', 0, %s
            )
            """,
            (
                batch_id,
                dw_load_id,
                Jsonb(details),
            ),
        )

    return dw_load_id, "START", "RUNNING"


def mark_failed(conn, dw_load_id, step, message):
    if not step.strip() or not message.strip():
        raise ValueError("Phải cung cấp tên bước và nội dung lỗi.")

    acquire_lock(conn)

    with conn.transaction():
        run = conn.execute(
            """
            SELECT source_batch_id, status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            FOR UPDATE
            """,
            (dw_load_id,),
        ).fetchone()

        if run is None:
            raise ValueError(f"Không tìm thấy DW load {dw_load_id}")

        source_batch_id, status = run

        if status != "RUNNING":
            raise ValueError(
                f"DW load {dw_load_id} đang {status}; "
                "chỉ chuyển RUNNING sang FAILED."
            )

        conn.execute(
            """
            UPDATE audit.dw_load
            SET status = 'FAILED',
                finished_at = clock_timestamp(),
                error_message = %s
            WHERE dw_load_id = %s
            """,
            (f"{step}: {message}", dw_load_id),
        )

        conn.execute(
            """
            INSERT INTO audit.data_quality_result (
                etl_batch_id,
                dw_load_id,
                table_name,
                rule_code,
                severity,
                status,
                affected_rows,
                details
            )
            VALUES (
                %s, %s, 'DW_PIPELINE',
                'DW_EXECUTION_ERROR',
                'ERROR', 'FAIL', 0, %s
            )
            """,
            (
                source_batch_id,
                dw_load_id,
                Jsonb({
                    "step": step,
                    "error_message": message,
                    "affected_rows_known": False,
                }),
            ),
        )


def show_status(conn, dw_load_id):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT dw_load_id,
                   source_batch_id,
                   pipeline_version,
                   scope_rule_version,
                   scope_file_sha256,
                   source_calendar_id,
                   status,
                   started_at,
                   finished_at,
                   error_message
            FROM audit.dw_load
            WHERE dw_load_id = %s
            """,
            (dw_load_id,),
        )
        result = cur.fetchone()

    if result is None:
        raise ValueError(f"Không tìm thấy DW load {dw_load_id}")

    print(json.dumps(
        result,
        ensure_ascii=False,
        indent=2,
        default=str,
    ))


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    start = commands.add_parser("start")
    start.add_argument("--batch-id", type=int, required=True)
    start.add_argument(
        "--scope-dir",
        type=Path,
        default=ROOT / "data/landing/fmcg_classification_v1_3",
    )
    start.add_argument(
        "--raw-dir",
        type=Path,
        default=ROOT / "data/raw/complete_journey",
    )

    status = commands.add_parser("status")
    status.add_argument("--dw-load-id", type=int, required=True)

    fail = commands.add_parser("fail")
    fail.add_argument("--dw-load-id", type=int, required=True)
    fail.add_argument("--step", required=True)
    fail.add_argument("--message", required=True)

    args = parser.parse_args()

    with connect_db() as conn:
        if args.command == "start":
            run_id, action, state = start_run(
                conn,
                args.batch_id,
                args.scope_dir.resolve(),
                args.raw_dir.resolve(),
            )
            print(
                f"\n{action} | dw_load_id={run_id} | {state}"
            )
            show_status(conn, run_id)

        elif args.command == "status":
            show_status(conn, args.dw_load_id)

        elif args.command == "fail":
            mark_failed(
                conn,
                args.dw_load_id,
                args.step,
                args.message,
            )
            print(f"FAILED | dw_load_id={args.dw_load_id}")


if __name__ == "__main__":
    main()