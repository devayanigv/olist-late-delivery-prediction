
import logging
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger("olist_etl")


def run_pipeline(engine):
    """Rebuild and validate the Olist warehouse from raw tables."""

    logger.info("Starting Olist warehouse pipeline")

    with engine.begin() as conn:

        # 1. Clear existing warehouse data safely
        logger.info("Clearing existing warehouse data")

        conn.execute(text("""
            TRUNCATE TABLE
                warehouse.fact_order_items,
                warehouse.fact_orders,
                warehouse.dim_customer,
                warehouse.dim_product,
                warehouse.dim_seller,
                warehouse.dim_date
            RESTART IDENTITY CASCADE;
        """))

        # 2. Load customer dimension
        conn.execute(text("""
            INSERT INTO warehouse.dim_customer (
                customer_id, customer_unique_id,
                zip_code_prefix, city, state
            )
            SELECT
                customer_id,
                customer_unique_id,
                LPAD(customer_zip_code_prefix::text, 5, '0'),
                customer_city,
                customer_state
            FROM raw.customers;
        """))

        # 3. Load seller dimension
        conn.execute(text("""
            INSERT INTO warehouse.dim_seller (
                seller_id, zip_code_prefix, city, state
            )
            SELECT
                seller_id,
                LPAD(seller_zip_code_prefix::text, 5, '0'),
                seller_city,
                seller_state
            FROM raw.sellers;
        """))

        # 4. Load product dimension
        conn.execute(text("""
            INSERT INTO warehouse.dim_product (
                product_id, category_name, category_name_english,
                product_name_length, product_description_length,
                product_photos_qty, product_weight_g, weight_quality,
                product_length_cm, product_height_cm, product_width_cm
            )
            SELECT
                p.product_id,
                COALESCE(p.product_category_name, 'Unknown'),
                COALESCE(c.product_category_name_english, 'Unknown'),
                p.product_name_lenght,
                p.product_description_lenght,
                p.product_photos_qty,
                CASE
                    WHEN p.product_weight_g > 0
                    THEN p.product_weight_g
                    ELSE NULL
                END,
                CASE
                    WHEN p.product_weight_g IS NULL THEN 'missing'
                    WHEN p.product_weight_g <= 0 THEN 'invalid'
                    ELSE 'valid'
                END,
                p.product_length_cm,
                p.product_height_cm,
                p.product_width_cm
            FROM raw.products p
            LEFT JOIN raw.category_translation c
                ON p.product_category_name = c.product_category_name;
        """))

        # 5. Generate and load date dimension
        conn.execute(text("""
            INSERT INTO warehouse.dim_date (date_key, full_date)
            VALUES (0, NULL);
        """))

        conn.execute(text("""
            WITH all_dates AS (
                SELECT order_purchase_timestamp::timestamp::date AS d
                FROM raw.orders

                UNION ALL
                SELECT order_approved_at::timestamp::date
                FROM raw.orders
                WHERE order_approved_at IS NOT NULL

                UNION ALL
                SELECT order_delivered_customer_date::timestamp::date
                FROM raw.orders
                WHERE order_delivered_customer_date IS NOT NULL

                UNION ALL
                SELECT order_estimated_delivery_date::timestamp::date
                FROM raw.orders

                UNION ALL
                SELECT shipping_limit_date::timestamp::date
                FROM raw.order_items
            ),
            date_bounds AS (
                SELECT MIN(d) AS min_date, MAX(d) AS max_date
                FROM all_dates
            ),
            calendar AS (
                SELECT generate_series(
                    min_date, max_date, INTERVAL '1 day'
                )::date AS d
                FROM date_bounds
            )
            INSERT INTO warehouse.dim_date (
                date_key, full_date, year, quarter, month,
                month_name, day_of_month, day_of_week,
                day_name, is_weekend
            )
            SELECT
                TO_CHAR(d, 'YYYYMMDD')::INTEGER,
                d,
                EXTRACT(YEAR FROM d)::INTEGER,
                EXTRACT(QUARTER FROM d)::INTEGER,
                EXTRACT(MONTH FROM d)::INTEGER,
                TRIM(TO_CHAR(d, 'Month')),
                EXTRACT(DAY FROM d)::INTEGER,
                EXTRACT(ISODOW FROM d)::INTEGER - 1,
                TRIM(TO_CHAR(d, 'Day')),
                EXTRACT(ISODOW FROM d) IN (6, 7)
            FROM calendar;
        """))

        # 6. Load order fact table
        conn.execute(text("""
            INSERT INTO warehouse.fact_orders (
                order_id, customer_key, purchase_date_key,
                approved_date_key, delivered_date_key,
                estimated_delivery_date_key, order_status,
                total_items, unique_products, unique_sellers,
                total_product_value, total_freight,
                total_payment_value, payment_records,
                max_installments, actual_delivery_days, is_late
            )
            SELECT
                o.order_id,
                dc.customer_key,
                TO_CHAR(
                    o.order_purchase_timestamp::timestamp::date,
                    'YYYYMMDD'
                )::INTEGER,
                CASE WHEN o.order_approved_at IS NOT NULL
                    THEN TO_CHAR(
                        o.order_approved_at::timestamp::date, 'YYYYMMDD'
                    )::INTEGER
                END,
                CASE WHEN o.order_delivered_customer_date IS NOT NULL
                    THEN TO_CHAR(
                        o.order_delivered_customer_date::timestamp::date,
                        'YYYYMMDD'
                    )::INTEGER
                END,
                TO_CHAR(
                    o.order_estimated_delivery_date::timestamp::date,
                    'YYYYMMDD'
                )::INTEGER,
                o.order_status,
                COALESCE(i.total_items, 0),
                COALESCE(i.unique_products, 0),
                COALESCE(i.unique_sellers, 0),
                i.total_product_value,
                i.total_freight,
                p.total_payment_value,
                p.payment_records,
                p.max_installments,
                CASE WHEN o.order_delivered_customer_date IS NOT NULL
                    THEN EXTRACT(EPOCH FROM (
                        o.order_delivered_customer_date::timestamp -
                        o.order_purchase_timestamp::timestamp
                    )) / 86400.0
                END,
                CASE WHEN o.order_delivered_customer_date IS NOT NULL
                    THEN o.order_delivered_customer_date::timestamp::date >
                         o.order_estimated_delivery_date::timestamp::date
                END
            FROM raw.orders o
            JOIN warehouse.dim_customer dc
                ON o.customer_id = dc.customer_id
            LEFT JOIN (
                SELECT
                    order_id,
                    COUNT(*) AS total_items,
                    COUNT(DISTINCT product_id) AS unique_products,
                    COUNT(DISTINCT seller_id) AS unique_sellers,
                    SUM(price) AS total_product_value,
                    SUM(freight_value) AS total_freight
                FROM raw.order_items
                GROUP BY order_id
            ) i ON o.order_id = i.order_id
            LEFT JOIN (
                SELECT
                    order_id,
                    SUM(payment_value) AS total_payment_value,
                    COUNT(*) AS payment_records,
                    MAX(payment_installments) AS max_installments
                FROM raw.order_payments
                GROUP BY order_id
            ) p ON o.order_id = p.order_id;
        """))

        # 7. Load order-item fact table
        conn.execute(text("""
            INSERT INTO warehouse.fact_order_items (
                order_key, order_id, order_item_id,
                customer_key, product_key, seller_key,
                purchase_date_key, shipping_limit_date_key,
                price, freight_value
            )
            SELECT
                fo.order_key,
                oi.order_id,
                oi.order_item_id::INTEGER,
                dc.customer_key,
                dp.product_key,
                ds.seller_key,
                TO_CHAR(
                    o.order_purchase_timestamp::timestamp::date,
                    'YYYYMMDD'
                )::INTEGER,
                TO_CHAR(
                    oi.shipping_limit_date::timestamp::date,
                    'YYYYMMDD'
                )::INTEGER,
                oi.price,
                oi.freight_value
            FROM raw.order_items oi
            JOIN raw.orders o
                ON oi.order_id = o.order_id
            JOIN warehouse.fact_orders fo
                ON oi.order_id = fo.order_id
            JOIN warehouse.dim_customer dc
                ON o.customer_id = dc.customer_id
            JOIN warehouse.dim_product dp
                ON oi.product_id = dp.product_id
            JOIN warehouse.dim_seller ds
                ON oi.seller_id = ds.seller_id;
        """))

        # 8. Row counts and quality checks
        tables = [
            "dim_customer", "dim_seller", "dim_product",
            "dim_date", "fact_orders", "fact_order_items"
        ]

        counts = {}
        for table in tables:
            counts[table] = conn.execute(
                text(f"SELECT COUNT(*) FROM warehouse.{table}")
            ).scalar_one()
            logger.info("%s: %s rows", table, counts[table])

        expected = {
            "dim_customer": 99441,
            "dim_seller": 3095,
            "dim_product": 32951,
            "fact_orders": 99441,
            "fact_order_items": 112650
        }

        for table, expected_count in expected.items():
            if counts[table] != expected_count:
                raise ValueError(
                    f"{table}: expected {expected_count}, "
                    f"got {counts[table]}"
                )

        if counts["dim_date"] < 2:
            raise ValueError("Date dimension is unexpectedly empty")

        invalid_items = conn.execute(text("""
            SELECT COUNT(*)
            FROM warehouse.fact_order_items f
            LEFT JOIN warehouse.fact_orders o
                ON f.order_key = o.order_key
            LEFT JOIN warehouse.dim_product p
                ON f.product_key = p.product_key
            LEFT JOIN warehouse.dim_seller s
                ON f.seller_key = s.seller_key
            LEFT JOIN warehouse.dim_customer c
                ON f.customer_key = c.customer_key
            WHERE o.order_key IS NULL
               OR p.product_key IS NULL
               OR s.seller_key IS NULL
               OR c.customer_key IS NULL;
        """)).scalar_one()

        if invalid_items != 0:
            raise ValueError(
                f"Found {invalid_items} invalid fact item relationships"
            )

        duplicate_items = conn.execute(text("""
            SELECT COUNT(*)
            FROM (
                SELECT order_id, order_item_id
                FROM warehouse.fact_order_items
                GROUP BY order_id, order_item_id
                HAVING COUNT(*) > 1
            ) duplicates;
        """)).scalar_one()

        if duplicate_items != 0:
            raise ValueError("Duplicate order items found")

        logger.info("All warehouse quality checks passed.")

    logger.info("Olist warehouse pipeline completed successfully.")
    return counts
