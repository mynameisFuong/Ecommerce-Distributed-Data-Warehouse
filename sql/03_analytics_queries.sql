SET search_path TO ecommerce_dw;

-- 1. Monthly revenue and order volume.
SELECT
    d.year,
    d.month,
    SUM(f.allocated_payment_value) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.quantity) AS total_items
FROM ecommerce_dw.fact_olist_orders f
JOIN ecommerce_dw.dim_date d ON f.purchase_date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

-- 2. Revenue by customer state.
SELECT
    c.customer_state,
    SUM(f.allocated_payment_value) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM ecommerce_dw.fact_olist_orders f
JOIN ecommerce_dw.dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.customer_state
ORDER BY total_revenue DESC;

-- 3. Top product categories by revenue.
SELECT
    p.product_category_name_english,
    SUM(f.allocated_payment_value) AS total_revenue,
    SUM(f.quantity) AS total_items,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM ecommerce_dw.fact_olist_orders f
JOIN ecommerce_dw.dim_product p ON f.product_id = p.product_id
GROUP BY p.product_category_name_english
ORDER BY total_revenue DESC
LIMIT 10;

-- 4. Average delivery time by customer state.
SELECT
    c.customer_state,
    AVG(f.delivery_days) AS avg_delivery_days,
    AVG(f.shipping_delay_days) AS avg_shipping_delay_days,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM fact_olist_orders f
JOIN dim_customer c ON f.customer_id = c.customer_id
WHERE f.delivery_days IS NOT NULL
GROUP BY c.customer_state
ORDER BY avg_delivery_days DESC;

-- 5. Seller performance by state.
SELECT
    s.seller_state,
    SUM(f.allocated_payment_value) AS total_revenue,
    AVG(f.review_score) AS avg_review_score,
    COUNT(DISTINCT f.seller_id) AS total_sellers
FROM fact_olist_orders f
JOIN dim_seller s ON f.seller_id = s.seller_id
GROUP BY s.seller_state
ORDER BY total_revenue DESC;

-- 6. Payment method distribution.
SELECT
    f.dominant_payment_type,
    COUNT(DISTINCT f.order_id) AS total_orders,
    SUM(f.allocated_payment_value) AS total_revenue
FROM fact_olist_orders f
GROUP BY f.dominant_payment_type
ORDER BY total_orders DESC;
