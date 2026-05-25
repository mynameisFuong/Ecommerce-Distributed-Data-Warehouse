param(
    [string]$CoordinatorContainer = "ecommerce-citus-coordinator",
    [string]$Database = "ecommerce_dw",
    [string]$User = "postgres"
)

$ErrorActionPreference = "Stop"

docker exec $CoordinatorContainer psql -U $User -d $Database -c "CREATE EXTENSION IF NOT EXISTS citus;"

$workers = @("citus-worker-1", "citus-worker-2", "citus-worker-3", "citus-worker-4")

foreach ($worker in $workers) {
    $sql = @"
SELECT citus_add_node('$worker', 5432)
WHERE NOT EXISTS (
    SELECT 1
    FROM pg_dist_node
    WHERE nodename = '$worker'
      AND nodeport = 5432
);
"@
    docker exec $CoordinatorContainer psql -U $User -d $Database -c $sql
}

docker exec $CoordinatorContainer psql -U $User -d $Database -c "SELECT nodeid, nodename, nodeport, isactive FROM pg_dist_node ORDER BY nodeid;"
