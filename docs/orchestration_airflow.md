# Airflow Orchestration

## Mục tiêu

Airflow được bổ sung để orchestration toàn bộ batch ETL pipeline cho Distributed Data Warehouse.

Pipeline được quản lý bởi DAG:

```text
ecommerce_distributed_dw_etl
```

DAG thực hiện luồng:

```text
extract_raw_files
    -> transform_to_star_schema
    -> load_to_citus
    -> verify_warehouse
```

## Các service Airflow

Airflow được triển khai trong `docker-compose.yml` với các service:

| Service | Vai trò |
|---|---|
| `airflow-postgres` | Metadata database của Airflow |
| `airflow-init` | Khởi tạo Airflow DB và tạo user admin |
| `airflow-webserver` | Airflow UI |
| `airflow-scheduler` | Scheduler thực thi DAG/task |

Airflow chạy chung Docker network với Citus cluster nên task `load_to_citus` kết nối trực tiếp tới coordinator bằng hostname nội bộ:

```text
citus-coordinator:5432
```

## Airflow UI

Truy cập Airflow UI:

```text
http://localhost:8080
```

Tài khoản demo:

```text
username: admin
password: admin
```

## DAG tasks

### 1. extract_raw_files

Gọi script:

```bash
python etl/extract.py
```

Nhiệm vụ:

- Kiểm tra các file raw CSV Olist có tồn tại.
- Ghi manifest vào `data/processed/extract_manifest.json`.

### 2. transform_to_star_schema

Gọi script:

```bash
python etl/transform.py
```

Nhiệm vụ:

- Đọc raw CSV.
- Làm sạch và chuẩn hóa dữ liệu.
- Tạo các bảng Star Schema dạng CSV trong `data/warehouse`.

Output:

```text
fact_olist_orders.csv
dim_customer.csv
dim_seller.csv
dim_product.csv
dim_date.csv
dim_payment.csv
dim_review.csv
```

### 3. load_to_citus

Gọi script:

```bash
python etl/load.py
```

Nhiệm vụ:

- Kết nối tới Citus coordinator.
- Đăng ký 4 worker nodes.
- Tạo schema warehouse.
- Tạo distributed/reference tables.
- Load CSV vào Citus.
- Apply lại access roles.

Task này sử dụng environment trong DAG:

```text
DW_HOST=citus-coordinator
DW_PORT=5432
DW_DATABASE=ecommerce_dw
DW_USER=postgres
DW_PASSWORD=postgres
```

### 4. verify_warehouse

Nhiệm vụ:

- Kết nối bằng `readonly_user`.
- Kiểm tra row count của `fact_olist_orders`.
- Assert kết quả phải bằng `112650`.

Query kiểm tra:

```sql
SELECT COUNT(*)
FROM ecommerce_dw.fact_olist_orders;
```

## Kết quả chạy thử

DAG run đã chạy thành công:

| Task | State |
|---|---|
| `extract_raw_files` | success |
| `transform_to_star_schema` | success |
| `load_to_citus` | success |
| `verify_warehouse` | success |

Kết quả kiểm tra sau DAG run:

```text
fact_olist_orders = 112650 rows
citus-worker-1 active = true
citus-worker-2 active = true
citus-worker-3 active = true
citus-worker-4 active = true
```

## Ý nghĩa trong hệ thống

Airflow đóng vai trò orchestration layer. Thay vì chạy thủ công từng script, Airflow quản lý thứ tự task, log, retry và trạng thái pipeline.

Trong project này, Airflow giúp chứng minh hệ thống có pipeline ETL end-to-end:

```text
Raw CSV -> Extract validation -> Transform Star Schema -> Load Distributed Warehouse -> Verify result
```

Nếu một task lỗi, Airflow ghi log chi tiết và có thể retry theo cấu hình DAG.