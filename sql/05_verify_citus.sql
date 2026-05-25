SET search_path TO ecommerce_dw;

SELECT COUNT(*) AS fact_olist_orders_count
FROM fact_olist_orders;

SELECT
    logicalrelid::regclass AS table_name,
    CASE partmethod
        WHEN 'h' THEN 'distributed'
        WHEN 'n' THEN 'reference'
        ELSE partmethod::text
    END AS citus_table_type,
    repmodel AS replication_model
FROM pg_dist_partition
ORDER BY table_name;

SELECT
    nodeid,
    nodename,
    nodeport,
    isactive
FROM pg_dist_node
ORDER BY nodeid;

SELECT
    logicalrelid::regclass AS table_name,
    COUNT(DISTINCT ps.shardid) AS shard_count,
    MIN(placement_count) AS min_placements_per_shard,
    MAX(placement_count) AS max_placements_per_shard
FROM pg_dist_partition dp
JOIN (
    SELECT shardid, COUNT(*) AS placement_count
    FROM pg_dist_placement
    GROUP BY shardid
) ps ON ps.shardid IN (
    SELECT shardid
    FROM pg_dist_shard ds
    WHERE ds.logicalrelid = dp.logicalrelid
)
GROUP BY logicalrelid
ORDER BY table_name;
