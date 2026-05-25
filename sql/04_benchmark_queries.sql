SET search_path TO ecommerce_dw;

-- Run each query with EXPLAIN ANALYZE and record execution time.
-- Compare the same queries on single-node PostgreSQL and Citus.

EXPLAIN ANALYZE
SELECT
    d.year,
    d.month,
    SUM(f.allocated_payment_value) AS total_revenue
FROM fact_olist_orders f
JOIN dim_date d ON f.purchase_date_key = d.date_key
GROUP BY d.year, d.month
ORDER BY d.year, d.month;

EXPLAIN ANALYZE
SELECT
    c.customer_state,
    SUM(f.allocated_payment_value) AS total_revenue,
    COUNT(DISTINCT f.order_id) AS total_orders
FROM fact_olist_orders f
JOIN dim_customer c ON f.customer_id = c.customer_id
GROUP BY c.customer_state
ORDER BY total_revenue DESC;

EXPLAIN ANALYZE
SELECT
    p.product_category_name_english,
    SUM(f.allocated_payment_value) AS total_revenue
FROM fact_olist_orders f
JOIN dim_product p ON f.product_id = p.product_id
GROUP BY p.product_category_name_english
ORDER BY total_revenue DESC
LIMIT 10;

EXPLAIN ANALYZE
SELECT
    s.seller_state,
    AVG(f.review_score) AS avg_review_score,
    AVG(f.delivery_days) AS avg_delivery_days,
    SUM(f.allocated_payment_value) AS total_revenue
FROM fact_olist_orders f
JOIN dim_seller s ON f.seller_id = s.seller_id
WHERE f.delivery_days IS NOT NULL
GROUP BY s.seller_state
ORDER BY total_revenue DESC;
