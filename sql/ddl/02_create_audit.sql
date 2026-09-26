BEGIN;

CREATE TABLE audit.etl_batch (
    etl_batch_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    dataset_name TEXT NOT NULL,
    source_manifest_hash TEXT NOT NULL
        CHECK (source_manifest_hash ~ '^[0-9a-f]{64}$'),
    pipeline_version TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    error_message TEXT,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK (status <> 'SUCCESS' OR finished_at IS NOT NULL)
);

-- Ngăn hai batch đang chạy/thành công cho cùng đầu vào và phiên bản.
-- Batch FAILED không ngăn việc thử lại.
CREATE UNIQUE INDEX uq_etl_batch_active_input
ON audit.etl_batch (
    dataset_name,
    source_manifest_hash,
    pipeline_version
)
WHERE status IN ('RUNNING', 'SUCCESS');


CREATE TABLE audit.etl_file_load (
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    source_file_name TEXT NOT NULL,
    source_file_sha256 TEXT NOT NULL
        CHECK (source_file_sha256 ~ '^[0-9a-f]{64}$'),
    source_object_name TEXT,
    target_table TEXT NOT NULL,
    source_row_count BIGINT CHECK (source_row_count >= 0),
    loaded_row_count BIGINT CHECK (loaded_row_count >= 0),
    source_timezone TEXT,
    status TEXT NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    error_message TEXT,
    PRIMARY KEY (etl_batch_id, source_file_name),
    CHECK (
        status <> 'SUCCESS'
        OR (
            source_row_count IS NOT NULL
            AND loaded_row_count IS NOT NULL
            AND source_row_count = loaded_row_count
        )
    )
);


CREATE TABLE audit.dw_load (
    dw_load_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    pipeline_version TEXT NOT NULL,
    scope_rule_version TEXT NOT NULL,
    scope_file_sha256 TEXT NOT NULL
        CHECK (scope_file_sha256 ~ '^[0-9a-f]{64}$'),
    source_calendar_id TEXT NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMPTZ,
    status TEXT NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'SUCCESS', 'FAILED')),
    error_message TEXT,
    CHECK (finished_at IS NULL OR finished_at >= started_at),
    CHECK (status <> 'SUCCESS' OR finished_at IS NOT NULL)
);


CREATE TABLE audit.data_quality_result (
    dq_result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    dw_load_id BIGINT REFERENCES audit.dw_load(dw_load_id),
    table_name TEXT NOT NULL,
    rule_code TEXT NOT NULL,
    severity TEXT NOT NULL
        CHECK (severity IN ('INFO', 'WARNING', 'ERROR')),
    status TEXT NOT NULL
        CHECK (status IN ('PASS', 'FAIL')),
    affected_rows BIGINT NOT NULL CHECK (affected_rows >= 0),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE audit.reconciliation_result (
    reconciliation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    dw_load_id BIGINT REFERENCES audit.dw_load(dw_load_id),
    source_name TEXT NOT NULL,
    target_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    source_value NUMERIC NOT NULL,
    target_value NUMERIC NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PASS', 'FAIL')),
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_dq_batch
    ON audit.data_quality_result(etl_batch_id);

CREATE INDEX ix_reconciliation_batch
    ON audit.reconciliation_result(etl_batch_id);

COMMIT;