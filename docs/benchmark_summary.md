# Benchmark Citus Query Results

Benchmark được chạy trên Citus cluster gồm:

- 1 coordinator: `ecommerce-citus-coordinator`
- 2 workers: `ecommerce-citus-worker-1`, `ecommerce-citus-worker-2`
- Fact table `fact_olist_orders`: 112,650 rows
- Fact table được distributed theo `order_id`
- Dimension tables được replicate dưới dạng reference tables

File kết quả chi tiết:

```text
docs/benchmark_citus_result.txt
```

## Kết quả benchmark

| Query | Mục đích | Execution Time |
|---|---:|---:|
| Q1 | Doanh thu theo tháng | 283.940 ms |
| Q2 | Doanh thu theo bang khách hàng | 836.011 ms |
| Q3 | Top danh mục sản phẩm theo doanh thu | 371.082 ms |
| Q4 | Hiệu suất seller theo bang | 255.948 ms |

## Nhận xét

Các query đều được Citus thực thi qua `Custom Scan (Citus Adaptive)` với `Task Count: 32`, cho thấy truy vấn đã được chia thành nhiều task phân tán trên các worker nodes.

`fact_olist_orders` là distributed table, còn các dimension như `dim_customer`, `dim_product`, `dim_seller`, `dim_date` là reference tables. Vì vậy, khi join fact với dimension, Citus có thể đẩy một phần xử lý xuống worker node và tổng hợp kết quả ở coordinator.

Query Q2 có thời gian cao nhất vì join với `dim_customer`, bảng dimension lớn nhất trong mô hình hiện tại với 99,441 rows, đồng thời có `COUNT(DISTINCT f.order_id)`.

Với dataset Olist chỉ khoảng hơn 112 nghìn dòng fact, thời gian truy vấn phân tán chưa chắc nhanh hơn single-node PostgreSQL vì vẫn có overhead điều phối task giữa coordinator và workers. Tuy nhiên kết quả benchmark chứng minh được mô hình distributed warehouse hoạt động đúng: fact table được phân mảnh, dimension tables được replicate, và query OLAP được thực thi qua distributed execution plan.
