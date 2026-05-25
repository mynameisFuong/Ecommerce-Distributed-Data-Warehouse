CREATE EXTENSION IF NOT EXISTS citus;
SET search_path TO ecommerce_dw;

-- Fact table: horizontally sharded by order_id.
-- All items of the same order stay on the same worker shard.
-- Replication factor 2 creates two placements for each shard across the worker pool.
SET citus.shard_replication_factor = 2;
SELECT create_distributed_table('ecommerce_dw.fact_olist_orders', 'order_id');

-- Dimension tables: replicated to every worker to make joins local.
SELECT create_reference_table('ecommerce_dw.dim_customer');
SELECT create_reference_table('ecommerce_dw.dim_seller');
SELECT create_reference_table('ecommerce_dw.dim_product');
SELECT create_reference_table('ecommerce_dw.dim_date');
SELECT create_reference_table('ecommerce_dw.dim_payment');
SELECT create_reference_table('ecommerce_dw.dim_review');
