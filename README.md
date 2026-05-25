# E-commerce Distributed Data Warehouse

Project Ã„â€˜Ã¡Â»â€œ ÃƒÂ¡n mÃƒÂ´n CÃ†Â¡ sÃ¡Â»Å¸ dÃ¡Â»Â¯ liÃ¡Â»â€¡u phÃƒÂ¢n tÃƒÂ¡n: xÃƒÂ¢y dÃ¡Â»Â±ng Data Warehouse phÃƒÂ¢n tÃƒÂ¡n cho dÃ¡Â»Â¯ liÃ¡Â»â€¡u thÃ†Â°Ã†Â¡ng mÃ¡ÂºÂ¡i Ã„â€˜iÃ¡Â»â€¡n tÃ¡Â»Â­ Olist.

## 1. Raw CSV cÃ¡ÂºÂ§n Ã„â€˜Ã¡ÂºÂ·t trong `data/raw`

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_customers_dataset.csv
olist_sellers_dataset.csv
olist_products_dataset.csv
product_category_name_translation.csv
```

File `product_category_name_translation.csv` lÃƒÂ  tÃƒÂ¹y chÃ¡Â»Ân, nhÃ†Â°ng nÃƒÂªn cÃƒÂ³ Ã„â€˜Ã¡Â»Æ’ dashboard dÃ¡Â»â€¦ Ã„â€˜Ã¡Â»Âc hÃ†Â¡n.

## 2. CÃƒÂ i thÃ†Â° viÃ¡Â»â€¡n Python

```powershell
cd C:\Users\ADMIN\Desktop\Final_Final_Final_Project
python -m pip install -r requirements.txt
```

## 3. ChÃ¡ÂºÂ¡y transform

```powershell
python etl/transform.py
```

KÃ¡ÂºÂ¿t quÃ¡ÂºÂ£ sÃ¡ÂºÂ½ Ã„â€˜Ã†Â°Ã¡Â»Â£c tÃ¡ÂºÂ¡o trong:

```text
data/warehouse
```

Bao gÃ¡Â»â€œm:

```text
fact_olist_orders.csv
dim_customer.csv
dim_seller.csv
dim_product.csv
dim_date.csv
dim_payment.csv
dim_review.csv
```

## 4. DÃ¡Â»Â±ng Citus cluster bÃ¡ÂºÂ±ng Docker

```powershell
docker compose up -d
docker compose ps
```

Cluster gÃ¡Â»â€œm:

```text
citus-coordinator: localhost:15432
citus-worker-1
citus-worker-2
```

ThÃƒÂ´ng tin kÃ¡ÂºÂ¿t nÃ¡Â»â€˜i mÃ¡ÂºÂ·c Ã„â€˜Ã¡Â»â€¹nh:

```text
host: 127.0.0.1
port: 15432
database: ecommerce_dw
user: postgres
password: postgres
```

## 5. Load dÃ¡Â»Â¯ liÃ¡Â»â€¡u vÃƒÂ o Distributed Warehouse

ChÃ¡ÂºÂ¡y lÃ¡ÂºÂ¡i transform trÃ†Â°Ã¡Â»â€ºc khi load Ã„â€˜Ã¡Â»Æ’ CSV khÃ¡Â»â€ºp schema mÃ¡Â»â€ºi nhÃ¡ÂºÂ¥t:

```powershell
python .\etl\transform.py
```

Sau Ã„â€˜ÃƒÂ³ load vÃƒÂ o Citus:

```powershell
python .\etl\load.py
```

Script `load.py` sÃ¡ÂºÂ½ tÃ¡Â»Â± Ã„â€˜Ã¡Â»â„¢ng:

```text
1. Ã„ÂÃ„Æ’ng kÃƒÂ½ citus-worker-1 vÃƒÂ  citus-worker-2 vÃƒÂ o coordinator.
2. ChÃ¡ÂºÂ¡y sql/01_create_schema.sql.
3. ChÃ¡ÂºÂ¡y sql/02_create_distributed_tables.sql.
4. COPY cÃƒÂ¡c file CSV trong data/warehouse vÃƒÂ o cÃƒÂ¡c bÃ¡ÂºÂ£ng warehouse.
```

NÃ¡ÂºÂ¿u muÃ¡Â»â€˜n Ã„â€˜Ã„Æ’ng kÃƒÂ½ worker thÃ¡Â»Â§ cÃƒÂ´ng Ã„â€˜Ã¡Â»Æ’ kiÃ¡Â»Æ’m tra:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\register_citus_workers.ps1
```

## 6. KiÃ¡Â»Æ’m tra schema warehouse

CÃƒÂ³ thÃ¡Â»Æ’ chÃ¡ÂºÂ¡y SQL trong container coordinator:

```powershell
docker exec -it ecommerce-citus-coordinator psql -U postgres -d ecommerce_dw
```

MÃ¡Â»â„¢t sÃ¡Â»â€˜ lÃ¡Â»â€¡nh kiÃ¡Â»Æ’m tra:

```sql
SELECT COUNT(*) FROM ecommerce_dw.fact_olist_orders;

SELECT
    logicalrelid::regclass AS table_name,
    CASE partmethod
        WHEN 'h' THEN 'distributed'
        WHEN 'n' THEN 'reference'
        ELSE partmethod::text
    END AS citus_table_type
FROM pg_dist_partition
ORDER BY table_name;

SELECT nodeid, nodename, nodeport, isactive
FROM pg_dist_node
ORDER BY nodeid;
```

## 7. Query phÃƒÂ¢n tÃƒÂ­ch

CÃƒÂ¡c query mÃ¡ÂºÂ«u nÃ¡ÂºÂ±m trong:

```text
sql/03_analytics_queries.sql
sql/04_benchmark_queries.sql
```

ChÃ¡ÂºÂ¡y file query phÃƒÂ¢n tÃƒÂ­ch:

```powershell
docker exec -i ecommerce-citus-coordinator psql -U postgres -d ecommerce_dw < .\sql\03_analytics_queries.sql
```

ChÃ¡ÂºÂ¡y file kiÃ¡Â»Æ’m tra Citus:

```powershell
docker exec -i ecommerce-citus-coordinator psql -U postgres -d ecommerce_dw < .\sql\05_verify_citus.sql
```
## 8. Airflow orchestration

Airflow được tích hợp để chạy pipeline ETL end-to-end.

Khởi động Airflow cùng Citus:

```powershell
docker compose up -d
```

Truy cập Airflow UI:

```text
http://localhost:8080
```

Tài khoản demo:

```text
username: admin
password: admin
```

DAG chính:

```text
ecommerce_distributed_dw_etl
```

Luồng task:

```text
extract_raw_files -> transform_to_star_schema -> load_to_citus -> verify_warehouse
```

Trigger DAG bằng CLI:

```powershell
docker exec ecommerce-airflow-scheduler airflow dags trigger ecommerce_distributed_dw_etl
```

Kiểm tra trạng thái DAG run:

```powershell
docker exec ecommerce-airflow-scheduler airflow dags list-runs -d ecommerce_distributed_dw_etl --no-backfill -o table
```

Tài liệu chi tiết nằm ở:

```text
docs/orchestration_airflow.md
```