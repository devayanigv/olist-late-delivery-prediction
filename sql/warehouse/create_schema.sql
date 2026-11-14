
CREATE SCHEMA IF NOT EXISTS warehouse;

-- ==========================================
-- 1. DATE DIMENSION
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE UNIQUE,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    day_of_month INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN
);

-- Unknown date record
INSERT INTO warehouse.dim_date (
    date_key, full_date
)
VALUES (0, NULL)
ON CONFLICT (date_key) DO NOTHING;


-- ==========================================
-- 2. CUSTOMER DIMENSION
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.dim_customer (
    customer_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    customer_id VARCHAR(50) UNIQUE NOT NULL,
    customer_unique_id VARCHAR(50),
    zip_code_prefix VARCHAR(5),
    city VARCHAR(100),
    state VARCHAR(10)
);


-- ==========================================
-- 3. PRODUCT DIMENSION
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.dim_product (
    product_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id VARCHAR(50) UNIQUE NOT NULL,
    category_name VARCHAR(100),
    category_name_english VARCHAR(100),
    product_name_length DOUBLE PRECISION,
    product_description_length DOUBLE PRECISION,
    product_photos_qty DOUBLE PRECISION,
    product_weight_g DOUBLE PRECISION,
    weight_quality VARCHAR(20) NOT NULL,
    product_length_cm DOUBLE PRECISION,
    product_height_cm DOUBLE PRECISION,
    product_width_cm DOUBLE PRECISION,

    CONSTRAINT chk_weight_quality
        CHECK (weight_quality IN ('valid', 'missing', 'invalid')),

    CONSTRAINT chk_product_weight
        CHECK (product_weight_g IS NULL OR product_weight_g > 0)
);


-- ==========================================
-- 4. SELLER DIMENSION
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.dim_seller (
    seller_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    seller_id VARCHAR(50) UNIQUE NOT NULL,
    zip_code_prefix VARCHAR(5),
    city VARCHAR(100),
    state VARCHAR(10)
);


-- ==========================================
-- 5. ORDERS FACT TABLE
-- Grain: one row per order
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.fact_orders (
    order_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    order_id VARCHAR(50) UNIQUE NOT NULL,

    customer_key BIGINT NOT NULL,
    purchase_date_key INTEGER NOT NULL,
    approved_date_key INTEGER,
    delivered_date_key INTEGER,
    estimated_delivery_date_key INTEGER,

    order_status VARCHAR(30),

    total_items INTEGER NOT NULL,
    unique_products INTEGER NOT NULL,
    unique_sellers INTEGER NOT NULL,

    total_product_value NUMERIC(14,2),
    total_freight NUMERIC(14,2),
    total_payment_value NUMERIC(14,2),

    payment_records INTEGER,
    max_installments INTEGER,

    actual_delivery_days NUMERIC(10,2),
    is_late BOOLEAN,

    CONSTRAINT fk_order_customer
        FOREIGN KEY (customer_key)
        REFERENCES warehouse.dim_customer(customer_key),

    CONSTRAINT fk_order_purchase_date
        FOREIGN KEY (purchase_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT fk_order_approved_date
        FOREIGN KEY (approved_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT fk_order_delivered_date
        FOREIGN KEY (delivered_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT fk_order_estimated_date
        FOREIGN KEY (estimated_delivery_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT chk_order_measures
        CHECK (
            total_items >= 0
            AND unique_products >= 0
            AND unique_sellers >= 0
        )
);


-- ==========================================
-- 6. ORDER ITEMS FACT TABLE
-- Grain: one row per order item
-- ==========================================

CREATE TABLE IF NOT EXISTS warehouse.fact_order_items (
    order_item_key BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    order_key BIGINT NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    order_item_id INTEGER NOT NULL,

    customer_key BIGINT NOT NULL,
    product_key BIGINT NOT NULL,
    seller_key BIGINT NOT NULL,
    purchase_date_key INTEGER NOT NULL,
    shipping_limit_date_key INTEGER NOT NULL,

    price NUMERIC(14,2) NOT NULL,
    freight_value NUMERIC(14,2) NOT NULL,

    CONSTRAINT uq_order_item
        UNIQUE (order_id, order_item_id),

    CONSTRAINT fk_item_order
        FOREIGN KEY (order_key)
        REFERENCES warehouse.fact_orders(order_key),

    CONSTRAINT fk_item_customer
        FOREIGN KEY (customer_key)
        REFERENCES warehouse.dim_customer(customer_key),

    CONSTRAINT fk_item_product
        FOREIGN KEY (product_key)
        REFERENCES warehouse.dim_product(product_key),

    CONSTRAINT fk_item_seller
        FOREIGN KEY (seller_key)
        REFERENCES warehouse.dim_seller(seller_key),

    CONSTRAINT fk_item_purchase_date
        FOREIGN KEY (purchase_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT fk_item_shipping_date
        FOREIGN KEY (shipping_limit_date_key)
        REFERENCES warehouse.dim_date(date_key),

    CONSTRAINT chk_item_values
        CHECK (price >= 0 AND freight_value >= 0)
);


-- ==========================================
-- INDEXES FOR COMMON JOINS
-- ==========================================

CREATE INDEX IF NOT EXISTS idx_fact_orders_customer
    ON warehouse.fact_orders(customer_key);

CREATE INDEX IF NOT EXISTS idx_fact_orders_purchase_date
    ON warehouse.fact_orders(purchase_date_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_product
    ON warehouse.fact_order_items(product_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_seller
    ON warehouse.fact_order_items(seller_key);

CREATE INDEX IF NOT EXISTS idx_fact_items_customer
    ON warehouse.fact_order_items(customer_key);
