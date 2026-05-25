DROP SCHEMA IF EXISTS ecommerce_dw CASCADE;
CREATE SCHEMA ecommerce_dw;
SET search_path TO ecommerce_dw;

CREATE TABLE dim_customer (
    customer_id TEXT PRIMARY KEY,
    customer_unique_id TEXT,
    customer_zip_code_prefix TEXT,
    customer_city TEXT,
    customer_state TEXT
);

CREATE TABLE dim_seller (
    seller_id TEXT PRIMARY KEY,
    seller_zip_code_prefix TEXT,
    seller_city TEXT,
    seller_state TEXT
);

CREATE TABLE dim_product (
    product_id TEXT PRIMARY KEY,
    product_category_name TEXT,
    product_category_name_english TEXT,
    product_weight_g NUMERIC(12, 2),
    product_length_cm NUMERIC(12, 2),
    product_height_cm NUMERIC(12, 2),
    product_width_cm NUMERIC(12, 2)
);

CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    month INTEGER NOT NULL,
    month_name TEXT NOT NULL,
    day INTEGER NOT NULL,
    day_of_week INTEGER NOT NULL,
    day_name TEXT NOT NULL,
    is_weekend BOOLEAN NOT NULL
);

CREATE TABLE dim_payment (
    payment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    payment_count INTEGER,
    payment_installments_max INTEGER,
    payment_value_total NUMERIC(14, 2),
    payment_types TEXT,
    dominant_payment_type TEXT
);

CREATE TABLE dim_review (
    review_key TEXT PRIMARY KEY,
    review_id TEXT,
    order_id TEXT NOT NULL,
    review_score NUMERIC(4, 2),
    review_creation_date DATE,
    review_answer_timestamp TIMESTAMP,
    review_comment_title TEXT,
    review_comment_message TEXT,
    review_creation_date_key INTEGER,
    review_answer_date_key INTEGER
);

CREATE TABLE fact_olist_orders (
    order_item_key BIGINT NOT NULL,
    order_id TEXT NOT NULL,
    order_item_id INTEGER NOT NULL,
    customer_id TEXT,
    seller_id TEXT,
    product_id TEXT,
    payment_id TEXT,
    review_key TEXT,
    review_id TEXT,
    purchase_date_key INTEGER,
    approved_date_key INTEGER,
    delivered_carrier_date_key INTEGER,
    delivered_customer_date_key INTEGER,
    estimated_delivery_date_key INTEGER,
    order_status TEXT,
    dominant_payment_type TEXT,
    quantity INTEGER,
    price NUMERIC(14, 2),
    freight_value NUMERIC(14, 2),
    item_total_value NUMERIC(14, 2),
    payment_value_total NUMERIC(14, 2),
    allocated_payment_value NUMERIC(14, 2),
    delivery_days NUMERIC(10, 2),
    shipping_delay_days NUMERIC(10, 2),
    review_score NUMERIC(4, 2),
    PRIMARY KEY (order_id, order_item_id, product_id, seller_id)
);

CREATE INDEX idx_fact_customer_id ON fact_olist_orders (customer_id);
CREATE INDEX idx_fact_seller_id ON fact_olist_orders (seller_id);
CREATE INDEX idx_fact_product_id ON fact_olist_orders (product_id);
CREATE INDEX idx_fact_purchase_date_key ON fact_olist_orders (purchase_date_key);
CREATE INDEX idx_fact_order_status ON fact_olist_orders (order_status);
