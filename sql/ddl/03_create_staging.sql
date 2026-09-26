BEGIN;

CREATE TABLE staging.stg_transactions (
    household_id TEXT,
    store_id TEXT,
    basket_id TEXT,
    product_id TEXT,
    quantity NUMERIC,
    sales_value NUMERIC,
    retail_disc NUMERIC,
    coupon_disc NUMERIC,
    coupon_match_disc NUMERIC,
    week INTEGER,
    transaction_timestamp TIMESTAMPTZ
);

CREATE TABLE staging.stg_promotions (
    product_id TEXT,
    store_id TEXT,
    display_location TEXT,
    mailer_location TEXT,
    week INTEGER
);

CREATE TABLE staging.stg_products (
    product_id TEXT,
    manufacturer_id TEXT,
    department TEXT,
    brand TEXT,
    product_category TEXT,
    product_type TEXT,
    package_size TEXT
);

CREATE TABLE staging.stg_demographics (
    household_id TEXT,
    age TEXT,
    income TEXT,
    home_ownership TEXT,
    marital_status TEXT,
    household_size TEXT,
    household_comp TEXT,
    kids_count TEXT
);

CREATE TABLE staging.stg_campaigns (
    campaign_id TEXT,
    household_id TEXT
);

CREATE TABLE staging.stg_campaign_descriptions (
    campaign_id TEXT,
    campaign_type TEXT,
    start_date DATE,
    end_date DATE
);

CREATE TABLE staging.stg_coupons (
    coupon_upc TEXT,
    product_id TEXT,
    campaign_id TEXT
);

CREATE TABLE staging.stg_coupon_redemptions (
    household_id TEXT,
    coupon_upc TEXT,
    campaign_id TEXT,
    redemption_date DATE
);

-- Thêm metadata và ràng buộc kỹ thuật cho cả tám bảng.
DO $$
DECLARE
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'stg_transactions',
        'stg_promotions',
        'stg_products',
        'stg_demographics',
        'stg_campaigns',
        'stg_campaign_descriptions',
        'stg_coupons',
        'stg_coupon_redemptions'
    ]
    LOOP
        EXECUTE format(
            'ALTER TABLE staging.%I
                ADD COLUMN staging_row_id BIGINT
                    GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                ADD COLUMN etl_batch_id BIGINT NOT NULL,
                ADD COLUMN source_file_name TEXT NOT NULL,
                ADD COLUMN source_object_name TEXT,
                ADD COLUMN source_row_number BIGINT NOT NULL
                    CHECK (source_row_number > 0),
                ADD COLUMN loaded_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                ADD UNIQUE (
                    etl_batch_id,
                    source_file_name,
                    source_row_number
                ),
                ADD FOREIGN KEY (etl_batch_id, source_file_name)
                    REFERENCES audit.etl_file_load (
                        etl_batch_id,
                        source_file_name
                    )',
            table_name
        );
    END LOOP;
END;
$$;

COMMIT;