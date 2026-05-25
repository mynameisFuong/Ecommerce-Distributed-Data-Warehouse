# Distributed + Replicated Citus Design

## Mục tiêu

Thiết kế mới đáp ứng đồng thời hai yêu cầu:

1. Dữ liệu phải được phân tán thật sự trên nhiều data nodes.
2. Hệ thống vẫn đọc được dữ liệu đầy đủ khi một worker node bị lỗi.

## Cluster hiện tại

| Container | Vai trò |
|---|---|
| `ecommerce-citus-coordinator` | Coordinator node: nhận query, lưu metadata phân tán, điều phối task |
| `ecommerce-citus-worker-1` | Worker/data node |
| `ecommerce-citus-worker-2` | Worker/data node |
| `ecommerce-citus-worker-3` | Worker/data node |
| `ecommerce-citus-worker-4` | Worker/data node |

## Cấu hình phân tán và replication

Trong `sql/02_create_distributed_tables.sql`:

```sql
SET citus.shard_replication_factor = 2;
SELECT create_distributed_table('ecommerce_dw.fact_olist_orders', 'order_id');
```

Ý nghĩa:

- `fact_olist_orders` được phân mảnh ngang theo `order_id`.
- Bảng fact có 32 shards.
- Mỗi shard có 2 placements, tức là 2 bản sao.
- Cluster có 4 workers, nên mỗi worker chỉ giữ một phần shard placements, không giữ toàn bộ fact table.
- Các dimension tables là reference tables nên được replicate sang cả 4 workers.

## Kết quả phân bố fact table

| Worker | Fact shard placements | Rows vật lý trên placements |
|---|---:|---:|
| `citus-worker-1` | 16 | 55,987 |
| `citus-worker-2` | 16 | 56,582 |
| `citus-worker-3` | 16 | 56,663 |
| `citus-worker-4` | 16 | 56,068 |

Tổng số dòng logic của fact table qua coordinator:

```text
fact_olist_orders = 112,650 rows
```

Tổng rows vật lý trên workers lớn hơn 112,650 vì mỗi shard có 2 bản sao.

## Kết quả placement metadata

| Table | Shard count | Total placements | Placements per shard |
|---|---:|---:|---:|
| `fact_olist_orders` | 32 | 64 | 2 |
| `dim_customer` | 1 | 4 | 4 |
| `dim_seller` | 1 | 4 | 4 |
| `dim_product` | 1 | 4 | 4 |
| `dim_date` | 1 | 4 | 4 |
| `dim_payment` | 1 | 4 | 4 |
| `dim_review` | 1 | 4 | 4 |

## Failure test

Dừng một worker:

```powershell
docker stop ecommerce-citus-worker-1
```

Query qua coordinator:

```sql
SELECT
    COUNT(*) AS fact_count_with_worker_1_down,
    SUM(allocated_payment_value) AS revenue_with_worker_1_down
FROM ecommerce_dw.fact_olist_orders;
```

Kết quả:

```text
fact_count_with_worker_1_down = 112650
revenue_with_worker_1_down = 15846280.53
```

Kết luận: khi một worker node bị dừng, coordinator vẫn có thể đọc dữ liệu từ bản sao shard còn lại trên các workers khác.

## Câu trả lời khi giảng viên hỏi

Hệ thống không chỉ replicate toàn bộ dữ liệu lên mọi worker. Với 4 workers và replication factor = 2, mỗi shard của fact table chỉ có 2 bản sao và được phân phối trên 2 trong 4 workers. Vì vậy mỗi worker chỉ giữ khoảng một nửa dữ liệu fact vật lý, còn toàn bộ cluster vẫn có đủ dữ liệu logic.

Cách này vừa đảm bảo phân tán dữ liệu thật sự, vừa có fault tolerance cho truy vấn đọc khi một worker bị lỗi.