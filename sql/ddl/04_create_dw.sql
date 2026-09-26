BEGIN;

-- Mã bắt buộc không rỗng.
CREATE DOMAIN dw.source_code AS TEXT
    CHECK (length(btrim(VALUE)) > 0);

-- Số lượng không âm, hữu hạn.
CREATE DOMAIN dw.quantity_value AS NUMERIC
    CHECK (
        VALUE >= 0
        AND VALUE < 'Infinity'::numeric
    );

-- Tiền không âm, hữu hạn và có độ chính xác tới cent.
CREATE DOMAIN dw.money_value AS NUMERIC
    CHECK (
        VALUE >= 0
        AND VALUE < 'Infinity'::numeric
        AND VALUE = round(VALUE, 2)
    );


-- =========================================================
-- DIMENSIONS
-- =========================================================

CREATE TABLE dw.dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id dw.source_code NOT NULL UNIQUE,
    manufacturer_id TEXT,
    department TEXT,
    brand TEXT,
    product_category TEXT,
    product_type TEXT,
    package_size TEXT,
    scope_status TEXT NOT NULL
        CHECK (scope_status IN ('IN_SCOPE', 'OUT_OF_SCOPE', 'REVIEW')),
    scope_rule_version TEXT NOT NULL,
    source_lookup_missing_flag BOOLEAN NOT NULL,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        NOT source_lookup_missing_flag
        OR scope_status = 'REVIEW'
    )
);


CREATE TABLE dw.dim_household (
    household_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    household_id dw.source_code NOT NULL UNIQUE,
    age TEXT,
    income TEXT,
    home_ownership TEXT,
    marital_status TEXT,
    household_size TEXT,
    household_comp TEXT,
    kids_count TEXT,
    demographics_available_flag BOOLEAN NOT NULL,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE dw.dim_store (
    store_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    store_id dw.source_code NOT NULL UNIQUE,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE dw.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE CHECK (isfinite(full_date)),
    day_of_month SMALLINT NOT NULL,
    month_number SMALLINT NOT NULL,
    quarter_number SMALLINT NOT NULL,
    calendar_year INTEGER NOT NULL,
    day_of_week SMALLINT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (calendar_year BETWEEN 1 AND 9999),

    CHECK (
        date_key =
            calendar_year * 10000
            + month_number * 100
            + day_of_month
    ),

    CHECK (day_of_month = EXTRACT(DAY FROM full_date)),
    CHECK (month_number = EXTRACT(MONTH FROM full_date)),
    CHECK (quarter_number = EXTRACT(QUARTER FROM full_date)),
    CHECK (calendar_year = EXTRACT(YEAR FROM full_date)),
    CHECK (day_of_week = EXTRACT(ISODOW FROM full_date))
);


CREATE TABLE dw.dim_week (
    week_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_calendar_id dw.source_code NOT NULL,
    source_week SMALLINT NOT NULL CHECK (source_week BETWEEN 1 AND 53),
    week_start_date DATE NOT NULL REFERENCES dw.dim_date(full_date),
    week_end_date DATE NOT NULL REFERENCES dw.dim_date(full_date),
    coverage_start_date DATE NOT NULL REFERENCES dw.dim_date(full_date),
    coverage_end_date DATE NOT NULL REFERENCES dw.dim_date(full_date),
    is_partial_coverage BOOLEAN NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (source_calendar_id, source_week),

    CHECK (EXTRACT(ISODOW FROM week_start_date) = 1),
    CHECK (week_end_date = week_start_date + 6),

    CHECK (
        coverage_start_date >= week_start_date
        AND coverage_end_date <= week_end_date
        AND coverage_start_date <= coverage_end_date
    ),

    CHECK (
        is_partial_coverage =
            ((coverage_end_date - coverage_start_date + 1) < 7)
    )
);


CREATE TABLE dw.dim_campaign (
    campaign_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id dw.source_code NOT NULL UNIQUE,
    campaign_type TEXT NOT NULL CHECK (length(btrim(campaign_type)) > 0),
    start_date DATE NOT NULL CHECK (isfinite(start_date)),
    end_date DATE NOT NULL CHECK (isfinite(end_date)),
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CHECK (start_date <= end_date),

    -- Dùng để kiểm tra cặp khóa/mã trong Dim_Coupon.
    UNIQUE (campaign_key, campaign_id)
);


CREATE TABLE dw.dim_coupon (
    coupon_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_key BIGINT NOT NULL,
    campaign_id dw.source_code NOT NULL,
    coupon_upc dw.source_code NOT NULL,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (campaign_id, coupon_upc),
    UNIQUE (coupon_key, campaign_key),

    FOREIGN KEY (campaign_key, campaign_id)
        REFERENCES dw.dim_campaign(campaign_key, campaign_id)
);


-- =========================================================
-- BRIDGES
-- =========================================================

CREATE TABLE dw.bridge_campaign_household (
    campaign_key BIGINT NOT NULL
        REFERENCES dw.dim_campaign(campaign_key),
    household_key BIGINT NOT NULL
        REFERENCES dw.dim_household(household_key),
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (campaign_key, household_key)
);


CREATE TABLE dw.bridge_coupon_product (
    coupon_key BIGINT NOT NULL
        REFERENCES dw.dim_coupon(coupon_key),
    product_key BIGINT NOT NULL
        REFERENCES dw.dim_product(product_key),
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    PRIMARY KEY (coupon_key, product_key)
);


-- =========================================================
-- FACT SALES
-- =========================================================

CREATE TABLE dw.fact_sales (
    sales_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    basket_id dw.source_code NOT NULL,

    product_key BIGINT NOT NULL
        REFERENCES dw.dim_product(product_key),
    household_key BIGINT NOT NULL
        REFERENCES dw.dim_household(household_key),
    store_key BIGINT NOT NULL
        REFERENCES dw.dim_store(store_key),
    date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),
    week_key BIGINT NOT NULL
        REFERENCES dw.dim_week(week_key),

    transaction_timestamp TIMESTAMPTZ NOT NULL
        CHECK (isfinite(transaction_timestamp)),

    quantity dw.quantity_value NOT NULL,
    sales_value dw.money_value NOT NULL,
    retail_disc dw.money_value NOT NULL,
    coupon_disc dw.money_value NOT NULL,
    coupon_match_disc dw.money_value NOT NULL,

    -- Sinh cờ từ measure để không bị lệch với giá trị thực tế.
    quantity_zero_flag BOOLEAN
        GENERATED ALWAYS AS (quantity = 0) STORED,

    quantity_zero_sales_positive_flag BOOLEAN
        GENERATED ALWAYS AS (
            quantity = 0 AND sales_value > 0
        ) STORED,

    positive_quantity_zero_sales_flag BOOLEAN
        GENERATED ALWAYS AS (
            quantity > 0 AND sales_value = 0
        ) STORED,

    coupon_above_sales_flag BOOLEAN
        GENERATED ALWAYS AS (
            coupon_disc > sales_value
        ) STORED,

    coupon_match_above_coupon_flag BOOLEAN
        GENERATED ALWAYS AS (
            coupon_match_disc > coupon_disc
        ) STORED,

    high_quantity_flag BOOLEAN
        GENERATED ALWAYS AS (quantity > 100) STORED,

    scope_rule_version TEXT NOT NULL,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (basket_id, product_key)
);


-- =========================================================
-- FACT PROMOTION WEEKLY
-- =========================================================

CREATE TABLE dw.fact_promotion_weekly (
    promotion_weekly_key BIGINT
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    product_key BIGINT NOT NULL
        REFERENCES dw.dim_product(product_key),
    store_key BIGINT NOT NULL
        REFERENCES dw.dim_store(store_key),
    week_key BIGINT NOT NULL
        REFERENCES dw.dim_week(week_key),

    has_display BOOLEAN,
    has_mailer BOOLEAN,

    display_location_codes TEXT[] NOT NULL,
    mailer_location_codes TEXT[] NOT NULL,

    source_row_count BIGINT NOT NULL CHECK (source_row_count > 0),

    multiple_source_rows_flag BOOLEAN
        GENERATED ALWAYS AS (source_row_count > 1) STORED,

    promotion_code_unknown_flag BOOLEAN NOT NULL,

    scope_rule_version TEXT NOT NULL,
    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (product_key, store_key, week_key),

    CHECK (
        promotion_code_unknown_flag
        OR (has_display IS NOT NULL AND has_mailer IS NOT NULL)
    )
);


-- =========================================================
-- FACT COUPON REDEMPTION
-- =========================================================

CREATE TABLE dw.fact_coupon_redemption (
    redemption_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    household_key BIGINT NOT NULL
        REFERENCES dw.dim_household(household_key),

    coupon_key BIGINT NOT NULL,

    campaign_key BIGINT NOT NULL
        REFERENCES dw.dim_campaign(campaign_key),

    redemption_date_key INTEGER NOT NULL
        REFERENCES dw.dim_date(date_key),

    redemption_record_count SMALLINT NOT NULL DEFAULT 1
        CHECK (redemption_record_count = 1),

    etl_batch_id BIGINT NOT NULL
        REFERENCES audit.etl_batch(etl_batch_id),
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (coupon_key, campaign_key)
        REFERENCES dw.dim_coupon(coupon_key, campaign_key),

    UNIQUE (
        household_key,
        coupon_key,
        campaign_key,
        redemption_date_key
    )
);


-- =========================================================
-- INDEXES CHO TRUY VẤN VÀ JOIN CHÍNH
-- =========================================================

CREATE INDEX ix_sales_date
    ON dw.fact_sales(date_key);

CREATE INDEX ix_sales_household
    ON dw.fact_sales(household_key);

CREATE INDEX ix_sales_promotion_join
    ON dw.fact_sales(product_key, store_key, week_key);

CREATE INDEX ix_promotion_week
    ON dw.fact_promotion_weekly(week_key);

CREATE INDEX ix_redemption_campaign_date
    ON dw.fact_coupon_redemption(campaign_key, redemption_date_key);

CREATE INDEX ix_campaign_household_reverse
    ON dw.bridge_campaign_household(household_key, campaign_key);

CREATE INDEX ix_coupon_product_reverse
    ON dw.bridge_coupon_product(product_key, coupon_key);

COMMIT;