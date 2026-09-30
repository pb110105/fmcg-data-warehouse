\set ON_ERROR_STOP on
\pset pager off

BEGIN;

-- Nhận batch_id từ lệnh chạy psql.
SELECT set_config('fmcg.source_batch_id', :'batch_id', true);

-- Dùng cùng khóa với chương trình nạp Staging.
SELECT pg_advisory_xact_lock(23133006);

DO $$
DECLARE
    v_batch BIGINT :=
        current_setting('fmcg.source_batch_id')::BIGINT;

    v_calendar TEXT := 'CJ_2017';
    v_start DATE;
    v_end DATE;
    v_bad BIGINT;
    v_date_count BIGINT;
    v_week_count BIGINT;
BEGIN
    -- =====================================================
    -- 1. KIỂM TRA BATCH NGUỒN
    -- =====================================================

    IF NOT EXISTS (
        SELECT 1
        FROM audit.etl_batch
        WHERE etl_batch_id = v_batch
          AND dataset_name = 'complete_journey'
          AND status = 'SUCCESS'
    ) THEN
        RAISE EXCEPTION
            'Batch % không phải Complete Journey SUCCESS', v_batch;
    END IF;

    IF (
        SELECT COUNT(*)
        FROM audit.etl_file_load
        WHERE etl_batch_id = v_batch
          AND status = 'SUCCESS'
          AND source_row_count = loaded_row_count
    ) <> 8 THEN
        RAISE EXCEPTION
            'Batch % chưa có đủ tám file đối soát thành công', v_batch;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM staging.stg_transactions
        WHERE etl_batch_id = v_batch
    ) THEN
        RAISE EXCEPTION 'Batch % không có giao dịch', v_batch;
    END IF;n

    -- =====================================================
    -- 2. TẠO LỊCH TUẦN KỲ VỌNG
    -- =====================================================

    CREATE TEMP TABLE expected_weeks ON COMMIT DROP AS
    SELECT
        'CJ_2017'::TEXT AS source_calendar_id,
        n::SMALLINT AS source_week,
        DATE '2016-12-26' + 7 * (n - 1) AS week_start_date,
        DATE '2016-12-26' + 7 * (n - 1) + 6 AS week_end_date,
        GREATEST(
            DATE '2016-12-26' + 7 * (n - 1),
            DATE '2017-01-01'
        ) AS coverage_start_date,
        LEAST(
            DATE '2016-12-26' + 7 * (n - 1) + 6,
            DATE '2017-12-31'
        ) AS coverage_end_date
    FROM generate_series(1, 53) AS g(n);

    -- =====================================================
    -- 3. KIỂM TRA NGÀY VÀ TUẦN NGUỒN
    -- =====================================================

    SELECT COUNT(*) INTO v_bad
    FROM staging.stg_transactions
    WHERE etl_batch_id = v_batch
      AND (
          transaction_timestamp IS NULL
          OR NOT isfinite(transaction_timestamp)
          OR week IS NULL
          OR week NOT BETWEEN 1 AND 53
      );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % giao dịch thiếu/sai timestamp hoặc week', v_bad;
    END IF;

    SELECT COUNT(*) INTO v_bad
    FROM staging.stg_transactions t
    LEFT JOIN expected_weeks w
        ON w.source_week = t.week
    WHERE t.etl_batch_id = v_batch
      AND (
          w.source_week IS NULL
          OR (t.transaction_timestamp
              AT TIME ZONE 'America/New_York')::DATE
             NOT BETWEEN w.coverage_start_date
                     AND w.coverage_end_date
      );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % giao dịch không khớp ngày/tuần CJ_2017', v_bad;
    END IF;

    SELECT COUNT(*) INTO v_bad
    FROM staging.stg_promotions
    WHERE etl_batch_id = v_batch
      AND (week IS NULL OR week NOT BETWEEN 1 AND 53);

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % dòng promotions thiếu/sai week', v_bad;
    END IF;

    SELECT COUNT(*) INTO v_bad
    FROM staging.stg_campaign_descriptions
    WHERE etl_batch_id = v_batch
      AND (
          start_date IS NULL
          OR end_date IS NULL
          OR NOT isfinite(start_date)
          OR NOT isfinite(end_date)
          OR start_date > end_date
      );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % chiến dịch có khoảng ngày không hợp lệ', v_bad;
    END IF;

    SELECT COUNT(*) INTO v_bad
    FROM staging.stg_coupon_redemptions
    WHERE etl_batch_id = v_batch
      AND (
          redemption_date IS NULL
          OR NOT isfinite(redemption_date)
      );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % bản ghi đổi coupon có ngày không hợp lệ', v_bad;
    END IF;

    -- =====================================================
    -- 4. XÁC ĐỊNH PHẠM VI DIM_DATE
    -- =====================================================

    WITH bounds AS (
        SELECT
            MIN(
                (transaction_timestamp
                 AT TIME ZONE 'America/New_York')::DATE
            ) AS first_date,
            MAX(
                (transaction_timestamp
                 AT TIME ZONE 'America/New_York')::DATE
            ) AS last_date
        FROM staging.stg_transactions
        WHERE etl_batch_id = v_batch

        UNION ALL

        SELECT MIN(start_date), MAX(end_date)
        FROM staging.stg_campaign_descriptions
        WHERE etl_batch_id = v_batch

        UNION ALL

        SELECT MIN(redemption_date), MAX(redemption_date)
        FROM staging.stg_coupon_redemptions
        WHERE etl_batch_id = v_batch

        UNION ALL

        SELECT MIN(week_start_date), MAX(week_end_date)
        FROM expected_weeks
    )
    SELECT MIN(first_date), MAX(last_date)
    INTO v_start, v_end
    FROM bounds;

    IF v_start < DATE '0001-01-01'
       OR v_end > DATE '9999-12-31' THEN
        RAISE EXCEPTION 'Phạm vi ngày vượt giới hạn Dim_Date';
    END IF;

    -- =====================================================
    -- 5. NẠP DIM_DATE
    -- =====================================================

    INSERT INTO dw.dim_date (
        date_key,
        full_date,
        day_of_month,
        month_number,
        quarter_number,
        calendar_year,
        day_of_week
    )
    SELECT
        EXTRACT(YEAR FROM d)::INTEGER * 10000
            + EXTRACT(MONTH FROM d)::INTEGER * 100
            + EXTRACT(DAY FROM d)::INTEGER,
        d,
        EXTRACT(DAY FROM d)::SMALLINT,
        EXTRACT(MONTH FROM d)::SMALLINT,
        EXTRACT(QUARTER FROM d)::SMALLINT,
        EXTRACT(YEAR FROM d)::INTEGER,
        EXTRACT(ISODOW FROM d)::SMALLINT
    FROM (
        SELECT v_start + n AS d
        FROM generate_series(0, v_end - v_start) AS g(n)
    ) calendar
    ON CONFLICT (full_date) DO NOTHING;

    -- =====================================================
    -- 6. KHÔNG GHI ĐÈ LỊCH TUẦN MÂU THUẪN
    -- =====================================================

    SELECT COUNT(*) INTO v_bad
    FROM dw.dim_week d
    JOIN expected_weeks e
      ON e.source_calendar_id = d.source_calendar_id
     AND e.source_week = d.source_week
    WHERE ROW(
        d.week_start_date,
        d.week_end_date,
        d.coverage_start_date,
        d.coverage_end_date,
        d.is_partial_coverage
    ) IS DISTINCT FROM ROW(
        e.week_start_date,
        e.week_end_date,
        e.coverage_start_date,
        e.coverage_end_date,
        (e.coverage_end_date - e.coverage_start_date + 1) < 7
    );

    IF v_bad > 0 THEN
        RAISE EXCEPTION
            'Có % tuần hiện tại mâu thuẫn mapping; dừng nạp', v_bad;
    END IF;

    -- =====================================================
    -- 7. NẠP DIM_WEEK, GIỮ ỔN ĐỊNH KHÓA ĐÃ CÓ
    -- =====================================================

    INSERT INTO dw.dim_week (
        source_calendar_id,
        source_week,
        week_start_date,
        week_end_date,
        coverage_start_date,
        coverage_end_date,
        is_partial_coverage
    )
    SELECT
        source_calendar_id,
        source_week,
        week_start_date,
        week_end_date,
        coverage_start_date,
        coverage_end_date,
        (coverage_end_date - coverage_start_date + 1) < 7
    FROM expected_weeks
    ORDER BY source_week
    ON CONFLICT (source_calendar_id, source_week) DO NOTHING;

    -- =====================================================
    -- 8. ĐỐI SOÁT
    -- =====================================================

    SELECT COUNT(*) INTO v_date_count
    FROM dw.dim_date
    WHERE full_date BETWEEN v_start AND v_end;

    IF v_date_count <> v_end - v_start + 1 THEN
        RAISE EXCEPTION 'Dim_Date chưa liên tục hoặc chưa đủ ngày';
    END IF;

    SELECT COUNT(*) INTO v_week_count
    FROM dw.dim_week
    WHERE source_calendar_id = v_calendar;

    IF v_week_count <> 53 THEN
        RAISE EXCEPTION
            'Dim_Week có % dòng, kỳ vọng 53', v_week_count;
    END IF;

    INSERT INTO audit.data_quality_result (
        etl_batch_id,
        table_name,
        rule_code,
        severity,
        status,
        affected_rows,
        details
    )
    VALUES (
        v_batch,
        'dw.dim_date,dw.dim_week',
        'CALENDAR_LOAD_V1',
        'INFO',
        'PASS',
        0,
        jsonb_build_object(
            'pipeline_version', 'calendar-1.0',
            'source_calendar_id', v_calendar,
            'source_timezone', 'America/New_York',
            'start_date', v_start,
            'end_date', v_end,
            'date_rows_in_range', v_date_count,
            'week_rows', v_week_count
        )
    );

    RAISE NOTICE 'PASS | Dim_Date | % đến % | % ngày',
        v_start, v_end, v_date_count;

    RAISE NOTICE 'PASS | Dim_Week | % | % tuần',
        v_calendar, v_week_count;
END;
$$;

COMMIT;

SELECT
    source_week,
    week_start_date,
    week_end_date,
    coverage_start_date,
    coverage_end_date,
    is_partial_coverage
FROM dw.dim_week
WHERE source_calendar_id = 'CJ_2017'
  AND source_week IN (1, 2, 53)
ORDER BY source_week;