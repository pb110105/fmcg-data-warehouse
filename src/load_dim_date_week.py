import argparse
from time import perf_counter

from load_staging import ROOT, connect_db
from dw_run import acquire_lock, mark_failed, PIPELINE_VERSION
from load_dim_household_store import print_load_result

SQL_FILE = ROOT / "sql" / "etl" / "01_load_date_week.sql"


def format_duration(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(int(minutes), 60)

    if hours:
        return f"{hours} giờ {minutes} phút {seconds:.1f} giây"
    if minutes:
        return f"{minutes} phút {seconds:.1f} giây"
    return f"{seconds:.1f} giây"


def read_calendar_sql():
    text = SQL_FILE.read_text(encoding="utf-8-sig")

    start_marker = "DO $$"
    end_marker = "\n$$;"

    if text.count(start_marker) != 1:
        raise ValueError("File SQL phải có đúng một khối DO $$.")

    start = text.index(start_marker)
    end = text.find(end_marker, start)

    if end == -1:
        raise ValueError("Không tìm thấy phần kết thúc khối SQL.")

    statement = text[start:end + len(end_marker)]

    # Bổ sung dw_load_id vào bản ghi audit của SQL hiện tại.
    old_columns = """        etl_batch_id,
        table_name,"""

    new_columns = """        etl_batch_id,
        dw_load_id,
        table_name,"""

    old_values = """        v_batch,
        'dw.dim_date,dw.dim_week',"""

    new_values = """        v_batch,
        current_setting('fmcg.dw_load_id')::BIGINT,
        'dw.dim_date,dw.dim_week',"""

    if (
        statement.count(old_columns) != 1
        or statement.count(old_values) != 1
    ):
        raise ValueError(
            "Cấu trúc audit trong file SQL đã thay đổi; "
            "cần kiểm tra trước khi chạy."
        )

    statement = statement.replace(old_columns, new_columns, 1)
    statement = statement.replace(old_values, new_values, 1)

    return statement


def calendar_counts(conn):
    date_rows = conn.execute(
        "SELECT COUNT(*) FROM dw.dim_date"
    ).fetchone()[0]

    week_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM dw.dim_week
        WHERE source_calendar_id = 'CJ_2017'
        """
    ).fetchone()[0]

    return date_rows, week_rows


def load_date_week(conn, run_id):
    started_at = perf_counter()
    calendar_sql = read_calendar_sql()

    print(
        f"ĐANG XỬ LÝ | Date và Week | dw_load_id={run_id}",
        flush=True,
    )

    with conn.transaction():
        conn.execute(
            "SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"
        )

        run = conn.execute(
            """
            SELECT source_batch_id, pipeline_version,
                   source_calendar_id, status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            FOR UPDATE
            """,
            (run_id,),
        ).fetchone()

        if run is None or run[3] != "RUNNING":
            raise ValueError(
                "DW load phải tồn tại và đang RUNNING."
            )

        batch_id, version, calendar_id, _ = run

        if version != PIPELINE_VERSION:
            raise ValueError(
                "Pipeline version không khớp nhật ký DW."
            )

        if calendar_id != "CJ_2017":
            raise ValueError(
                "Bước tạo lịch hiện tại chỉ hỗ trợ CJ_2017."
            )

        conn.execute(
            """
            SELECT set_config(
                'fmcg.source_batch_id', %s, true
            )
            """,
            (str(batch_id),),
        )

        conn.execute(
            """
            SELECT set_config(
                'fmcg.dw_load_id', %s, true
            )
            """,
            (str(run_id),),
        )

        dates_before, weeks_before = calendar_counts(conn)

        # Giữ nguyên kiểm tra và quy tắc tạo lịch trong SQL.
        conn.execute(calendar_sql, prepare=False)

        dates_after, weeks_after = calendar_counts(conn)

    # Chỉ thông báo PASS sau khi transaction commit thành công.
    print_load_result(
        "dim_date",
        dates_after,
        dates_after - dates_before,
        dates_before,
    )

    print_load_result(
        "dim_week",
        weeks_after,
        weeks_after - weeks_before,
        weeks_before,
    )

    print(
        f"HOÀN TẤT | Date và Week"
        f" | {format_duration(perf_counter() - started_at)}"
        f" | dw_load_id={run_id} vẫn RUNNING",
        flush=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Nạp Date và Week theo lần chạy DW."
    )
    parser.add_argument(
        "--dw-load-id",
        type=int,
        required=True,
    )
    args = parser.parse_args()

    if args.dw_load_id <= 0:
        parser.error("--dw-load-id phải lớn hơn 0.")

    with connect_db() as conn:
        # Dùng cùng khóa với các loader khác.
        acquire_lock(conn)

        state = conn.execute(
            """
            SELECT status
            FROM audit.dw_load
            WHERE dw_load_id = %s
            """,
            (args.dw_load_id,),
        ).fetchone()

        if state is None or state[0] != "RUNNING":
            raise ValueError(
                "DW load phải tồn tại và đang RUNNING."
            )

        try:
            load_date_week(conn, args.dw_load_id)
        except Exception as exc:
            mark_failed(
                conn,
                args.dw_load_id,
                "load_dim_date_week",
                f"{type(exc).__name__}: {exc}",
            )
            raise


if __name__ == "__main__":
    main()