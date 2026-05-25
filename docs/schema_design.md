# Thiết kế Star Schema cho Distributed Data Warehouse

## 1. Mục tiêu thiết kế

Kho dữ liệu được thiết kế để phục vụ phân tích dữ liệu thương mại điện tử từ bộ dữ liệu Olist. Mô hình được chọn là Star Schema vì dễ triển khai, dễ tối ưu truy vấn OLAP và phù hợp với kiến trúc phân tán bằng PostgreSQL/Citus.

Mục tiêu chính:

- Phân tích doanh thu theo thời gian, khu vực, sản phẩm, seller và phương thức thanh toán.
- Phân tích số lượng đơn hàng, số lượng sản phẩm bán ra và thời gian giao hàng.
- Minh họa cơ chế phân tán dữ liệu trong CSDL phân tán.

## 2. Grain của fact table

Fact table chính là `fact_olist_orders`.

Grain được chọn:

> Mỗi dòng trong fact table tương ứng với một item trong một order.

Khóa tự nhiên của grain:

```text
order_id + order_item_id + product_id + seller_id
```

Lý do chọn grain này:

- Giữ được chi tiết sản phẩm và seller trong từng đơn hàng.
- Có thể tổng hợp lên mức order, customer, product, seller, date.
- Tránh làm mất thông tin khi một đơn hàng có nhiều sản phẩm.
- Phù hợp để phân mảnh ngang theo `order_id` trong Citus.

## 3. Bảng fact

### fact_olist_orders

| Cột | Ý nghĩa |
|---|---|
| `order_item_key` | Surrogate key cho từng dòng fact |
| `order_id` | Mã đơn hàng, đồng thời là distribution key |
| `order_item_id` | Thứ tự item trong đơn hàng |
| `customer_id` | Khóa liên kết tới `dim_customer` |
| `seller_id` | Khóa liên kết tới `dim_seller` |
| `product_id` | Khóa liên kết tới `dim_product` |
| `payment_id` | Khóa liên kết tới `dim_payment`, dùng `order_id` |
| `review_key` | Khóa liên kết ổn định tới `dim_review`, dùng `order_id` |
| `review_id` | Mã review gốc trong Olist |
| `purchase_date_key` | Khóa ngày đặt hàng |
| `approved_date_key` | Khóa ngày duyệt đơn |
| `delivered_carrier_date_key` | Khóa ngày giao cho carrier |
| `delivered_customer_date_key` | Khóa ngày giao tới khách |
| `estimated_delivery_date_key` | Khóa ngày dự kiến giao |
| `order_status` | Trạng thái đơn hàng |
| `dominant_payment_type` | Phương thức thanh toán chính |
| `quantity` | Số lượng item, mặc định 1 |
| `price` | Giá item |
| `freight_value` | Phí vận chuyển của item |
| `item_total_value` | `price + freight_value` |
| `payment_value_total` | Tổng giá trị thanh toán của toàn order |
| `allocated_payment_value` | Giá trị thanh toán được phân bổ cho từng item |
| `delivery_days` | Số ngày từ lúc mua tới lúc nhận hàng |
| `shipping_delay_days` | Số ngày trễ so với ngày dự kiến |
| `review_score` | Điểm đánh giá của order |

Lưu ý: `payment_value_total` là measure cấp order. Khi phân tích doanh thu theo item/product/seller, nên dùng `allocated_payment_value` để tránh nhân đôi doanh thu với đơn hàng có nhiều item.

## 4. Các bảng dimension

### dim_customer

Lưu thông tin khách hàng và khu vực của khách hàng.

Khóa chính: `customer_id`

Các thuộc tính chính:

- `customer_unique_id`
- `customer_zip_code_prefix`
- `customer_city`
- `customer_state`

### dim_seller

Lưu thông tin seller và khu vực của seller.

Khóa chính: `seller_id`

Các thuộc tính chính:

- `seller_zip_code_prefix`
- `seller_city`
- `seller_state`

### dim_product

Lưu thông tin sản phẩm và danh mục sản phẩm.

Khóa chính: `product_id`

Các thuộc tính chính:

- `product_category_name`
- `product_category_name_english`
- `product_weight_g`
- `product_length_cm`
- `product_height_cm`
- `product_width_cm`

### dim_date

Lưu calendar dimension để phân tích theo ngày, tháng, quý, năm.

Khóa chính: `date_key`

Định dạng `date_key`: `YYYYMMDD`

Ví dụ:

```text
20180921
```

### dim_payment

Lưu thông tin thanh toán đã được aggregate theo `order_id`.

Khóa chính: `payment_id`

Trong thiết kế này, `payment_id = order_id`.

Lý do aggregate theo order:

- Một order có thể có nhiều dòng payment.
- Fact table đang ở grain order item, nếu join trực tiếp payment detail sẽ gây nhân dòng.
- Aggregate trước giúp fact table ổn định và không bị sai doanh thu.

### dim_review

Lưu thông tin review của order.

Khóa chính: `review_key`

Trong thiết kế này, `review_key = order_id`. Trường `review_id` vẫn được giữ lại như mã review gốc của bộ dữ liệu Olist.

Với order có nhiều review, script transform giữ review mới nhất theo `review_creation_date` để giữ quan hệ một order - một review trong mô hình Star Schema.

## 5. Thiết kế phân tán dữ liệu

Hệ thống sử dụng Citus để xây dựng Distributed Data Warehouse.

### Bảng phân tán

`fact_olist_orders` là bảng lớn nhất, được phân tán ngang theo `order_id`:

```sql
SELECT create_distributed_table('ecommerce_dw.fact_olist_orders', 'order_id');
```

Lý do chọn `order_id`:

- Các item thuộc cùng một order nằm cùng shard.
- Phù hợp với grain của fact table.
- Giúp các truy vấn tổng hợp theo order không phải gom dữ liệu từ nhiều shard cho cùng một đơn hàng.

### Bảng reference

Các bảng dimension được replicate tới mọi worker node:

```sql
SELECT create_reference_table('ecommerce_dw.dim_customer');
SELECT create_reference_table('ecommerce_dw.dim_seller');
SELECT create_reference_table('ecommerce_dw.dim_product');
SELECT create_reference_table('ecommerce_dw.dim_date');
SELECT create_reference_table('ecommerce_dw.dim_payment');
SELECT create_reference_table('ecommerce_dw.dim_review');
```

Lý do:

- Dimension tables nhỏ hơn fact table.
- Replication giúp join giữa fact và dimension được thực hiện local trên worker.
- Phù hợp với mô hình Star Schema trong OLAP.

## 6. File đầu ra từ transform

Script `etl/transform.py` tạo các file CSV sau trong `data/warehouse`:

```text
fact_olist_orders.csv
dim_customer.csv
dim_seller.csv
dim_product.csv
dim_date.csv
dim_payment.csv
dim_review.csv
```

Các file này là đầu vào cho bước Load vào PostgreSQL/Citus.
