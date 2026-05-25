# Citus Shard Replication Test

## Mục tiêu

Bổ sung replication cho `fact_olist_orders` để khi một worker node bị dừng, các truy vấn đọc vẫn trả về dữ liệu đầy đủ.

## Cấu hình đã áp dụng

Trong `sql/02_create_distributed_tables.sql`:

```sql
SET citus.shard_replication_factor = 2;
SELECT create_distributed_table('ecommerce_dw.fact_olist_orders', 'order_id');
```

Ý nghĩa:

- `fact_olist_orders` vẫn được phân mảnh ngang theo `order_id`.
- Mỗi shard của fact table có 2 placements.
- Với 2 worker nodes, mỗi shard có một bản sao trên mỗi worker.
- Các bảng dimension vẫn là reference tables nên cũng được replicate sang các workers.

## Kết quả kiểm tra placement

```text
fact_olist_orders shard_count = 32
min_placements_per_shard = 2
max_placements_per_shard = 2
```

Điều này chứng minh mỗi shard của `fact_olist_orders` đã có 2 bản sao.

## Failure test

Dừng worker 1:

```powershell
docker stop ecommerce-citus-worker-1
```

Chạy query qua coordinator:

```sql
SELECT COUNT(*) AS fact_count_with_worker_1_down
FROM ecommerce_dw.fact_olist_orders;
```

Kết quả:

```text
fact_count_with_worker_1_down = 112650
```

Tổng doanh thu vẫn truy vấn được:

```sql
SELECT SUM(allocated_payment_value) AS revenue_with_worker_1_down
FROM ecommerce_dw.fact_olist_orders;
```

Kết quả:

```text
revenue_with_worker_1_down = 15846280.53
```

Sau đó bật lại worker:

```powershell
docker start ecommerce-citus-worker-1
```

## Nhận xét

Sau khi bật shard replication factor = 2, hệ thống có thể phục vụ các truy vấn đọc khi một worker node bị dừng. Coordinator có thể dùng shard placement còn lại trên worker còn sống để trả về kết quả đầy đủ.

Khi worker bị dừng, Citus có thể in warning do không kết nối được tới worker đó, nhưng truy vấn vẫn hoàn tất nhờ bản sao shard còn lại.

Lưu ý: cấu hình này phù hợp cho demo fault tolerance ở mức đọc dữ liệu. Trong môi trường production, vẫn cần bổ sung high availability đầy đủ cho coordinator, worker PostgreSQL, persistent volumes, backup/restore và cơ chế failover tự động.