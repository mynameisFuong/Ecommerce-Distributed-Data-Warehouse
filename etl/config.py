from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
WAREHOUSE_DIR = DATA_DIR / "warehouse"

RAW_FILES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}

WAREHOUSE_FILES = {
    "fact_orders": "fact_olist_orders.csv",
    "dim_customer": "dim_customer.csv",
    "dim_seller": "dim_seller.csv",
    "dim_product": "dim_product.csv",
    "dim_date": "dim_date.csv",
    "dim_payment": "dim_payment.csv",
    "dim_review": "dim_review.csv",
}
