import argparse
from pathlib import Path

import pandas as pd

try:
    from .config import RAW_DIR, RAW_FILES, WAREHOUSE_DIR, WAREHOUSE_FILES
except ImportError:
    from config import RAW_DIR, RAW_FILES, WAREHOUSE_DIR, WAREHOUSE_FILES


REQUIRED_TABLES = [
    "orders",
    "order_items",
    "payments",
    "reviews",
    "customers",
    "sellers",
    "products",
]

ORDER_DATE_COLUMNS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=str,
        keep_default_na=False,
        na_values=[""],
        low_memory=False,
    )


def require_columns(df, table_name, required_columns):
    missing_columns = []

    for col in required_columns:
        if col not in df.columns:
            missing_columns.append(col)

    if missing_columns:
        raise ValueError(
            f"{table_name} thieu cot: {', '.join(missing_columns)}"
        )


def to_number(column, default=None):
    numbers = pd.to_numeric(column, errors="coerce")

    if default is not None:
        numbers = numbers.fillna(default)

    return numbers


def to_datetime(column):
    return pd.to_datetime(column, errors="coerce")


def to_date_key(column):
    dates = to_datetime(column)
    return dates.dt.strftime("%Y%m%d").astype("Int64")


def fill_text(column, default="unknown"):
    return column.fillna(default).replace("", default)


def load_raw_tables(raw_dir):
    missing_files = []
    tables = {}

    for table_name in REQUIRED_TABLES:
        file_name = RAW_FILES[table_name]
        file_path = raw_dir / file_name

        if not file_path.exists():
            missing_files.append(str(file_path))
        else:
            tables[table_name] = read_csv(file_path)
    
    if missing_files:
        raise FileNotFoundError("Thieu file CSV:\n" + "\n".join(missing_files))

    translation_file = raw_dir / RAW_FILES["category_translation"]
    if not translation_file.exists():
        tables["category_translation"] = read_csv(translation_file)

    return tables

def build_dim_customer(customers):
    require_columns(
        customers,
        "customers",
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ],
    )

    dim = customers[
        [
            "customer_id",
            "customer_unique_id",
            "customer_zip_code_prefix",
            "customer_city",
            "customer_state",
        ]
    ].drop_duplicates("customer_id")

    dim["customer_city"] = fill_text(dim["customer_city"])
    dim["customer_state"] = fill_text(dim["customer_state"])
    return dim.sort_values("customer_id").reset_index(drop=True)


def build_dim_seller(sellers):
    require_columns(
        sellers,
        "sellers",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    )

    dim = sellers[
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"]
    ].drop_duplicates("seller_id")

    dim["seller_city"] = fill_text(dim["seller_city"])
    dim["seller_state"] = fill_text(dim["seller_state"])
    return dim.sort_values("seller_id").reset_index(drop=True)


def build_dim_product(products, translation):
    require_columns(
        products,
        "products",
        [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ],
    )

    dim = products[
        [
            "product_id",
            "product_category_name",
            "product_weight_g",
            "product_length_cm",
            "product_height_cm",
            "product_width_cm",
        ]
    ].drop_duplicates("product_id")

    dim["product_category_name"] = fill_text(dim["product_category_name"])

    if translation is not None:
        require_columns(
            translation,
            "category_translation",
            ["product_category_name", "product_category_name_english"],
        )
        dim = dim.merge(
            translation.drop_duplicates("product_category_name"),
            on="product_category_name",
            how="left",
        )
    else:
        dim["product_category_name_english"] = dim["product_category_name"]

    dim["product_category_name_english"] = fill_text(
        dim["product_category_name_english"]
    )

    metric_columns = [
        "product_weight_g",
        "product_length_cm",
        "product_height_cm",
        "product_width_cm",
    ]
    for column in metric_columns:
        dim[column] = to_number(dim[column])

    return dim.sort_values("product_id").reset_index(drop=True)


def build_dim_payment(payments):
    require_columns(
        payments,
        "payments",
        [
            "order_id",
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
    )

    df = payments.copy()
    df["payment_value"] = to_number(df["payment_value"], default=0)
    df["payment_installments"] = to_number(df["payment_installments"], default=0)
    df["payment_type"] = fill_text(df["payment_type"])

    grouped = df.groupby("order_id", as_index=False).agg(
        payment_count=("payment_sequential", "count"),
        payment_installments_max=("payment_installments", "max"),
        payment_value_total=("payment_value", "sum"),
    )

    payment_types = (
        df.groupby("order_id")["payment_type"]
        .apply(lambda values: "|".join(sorted(set(values.dropna()))))
        .reset_index(name="payment_types")
    )

    dominant_type = (
        df.groupby("order_id")["payment_type"]
        .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else "unknown")
        .reset_index(name="dominant_payment_type")
    )

    dim = grouped.merge(payment_types, on="order_id", how="left").merge(
        dominant_type, on="order_id", how="left"
    )
    dim.insert(0, "payment_id", dim["order_id"])

    dim["payment_value_total"] = dim["payment_value_total"].round(2)
    dim["payment_installments_max"] = dim["payment_installments_max"].astype("Int64")
    dim["payment_count"] = dim["payment_count"].astype("Int64")
    return dim.sort_values("payment_id").reset_index(drop=True)


def build_dim_review(reviews):
    require_columns(
        reviews,
        "reviews",
        [
            "review_id",
            "order_id",
            "review_score",
            "review_creation_date",
            "review_answer_timestamp",
        ],
    )

    df = reviews.copy()
    df["review_score"] = to_number(df["review_score"])
    df["review_creation_date"] = to_datetime(df["review_creation_date"])
    df["review_answer_timestamp"] = to_datetime(df["review_answer_timestamp"])

    # Keep one review per order to preserve a clean star-schema relationship.
    df = df.sort_values(["order_id", "review_creation_date", "review_id"])
    latest = df.groupby("order_id", as_index=False).tail(1).copy()

    for optional_column in ["review_comment_title", "review_comment_message"]:
        if optional_column not in latest.columns:
            latest[optional_column] = pd.NA

    columns = [
        "review_id",
        "order_id",
        "review_score",
        "review_creation_date",
        "review_answer_timestamp",
        "review_comment_title",
        "review_comment_message",
    ]

    dim = latest[columns].copy()
    dim.insert(0, "review_key", dim["order_id"])
    dim["review_creation_date_key"] = to_date_key(dim["review_creation_date"])
    dim["review_answer_date_key"] = to_date_key(dim["review_answer_timestamp"])
    dim["review_creation_date"] = dim["review_creation_date"].dt.date
    dim["review_answer_timestamp"] = dim["review_answer_timestamp"].dt.strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    return dim.sort_values("review_key").reset_index(drop=True)


def build_dim_date(*date_series: pd.Series) -> pd.DataFrame:
    all_dates = pd.concat([to_datetime(series) for series in date_series], ignore_index=True)
    dates = all_dates.dropna().dt.normalize().drop_duplicates().sort_values()

    dim = pd.DataFrame({"full_date": dates})
    dim["date_key"] = dim["full_date"].dt.strftime("%Y%m%d").astype(int)
    dim["year"] = dim["full_date"].dt.year
    dim["quarter"] = dim["full_date"].dt.quarter
    dim["month"] = dim["full_date"].dt.month
    dim["month_name"] = dim["full_date"].dt.month_name()
    dim["day"] = dim["full_date"].dt.day
    dim["day_of_week"] = dim["full_date"].dt.dayofweek + 1
    dim["day_name"] = dim["full_date"].dt.day_name()
    dim["is_weekend"] = dim["day_of_week"].isin([6, 7])
    dim["full_date"] = dim["full_date"].dt.date

    return dim[
        [
            "date_key",
            "full_date",
            "year",
            "quarter",
            "month",
            "month_name",
            "day",
            "day_of_week",
            "day_name",
            "is_weekend",
        ]
    ].reset_index(drop=True)


def build_fact_orders(orders, order_items, dim_payment, dim_review):
    require_columns(
        orders,
        "orders",
        ["order_id", "customer_id", "order_status", *ORDER_DATE_COLUMNS],
    )
    require_columns(
        order_items,
        "order_items",
        ["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
    )

    orders_clean = orders.drop_duplicates("order_id").copy()
    for column in ORDER_DATE_COLUMNS:
        orders_clean[column] = to_datetime(orders_clean[column])

    items = order_items.copy()
    items["order_item_id"] = to_number(items["order_item_id"], default=0).astype("Int64")
    items["price"] = to_number(items["price"], default=0)
    items["freight_value"] = to_number(items["freight_value"], default=0)
    items["item_total_value"] = items["price"] + items["freight_value"]

    fact = items.merge(
        orders_clean[
            [
                "order_id",
                "customer_id",
                "order_status",
                *ORDER_DATE_COLUMNS,
            ]
        ],
        on="order_id",
        how="left",
    )

    fact = fact.merge(
        dim_payment[
            [
                "payment_id",
                "order_id",
                "payment_value_total",
                "dominant_payment_type",
            ]
        ],
        on="order_id",
        how="left",
    )

    fact = fact.merge(
        dim_review[["review_key", "review_id", "order_id", "review_score"]],
        on="order_id",
        how="left",
    )

    fact["purchase_date_key"] = to_date_key(fact["order_purchase_timestamp"])
    fact["approved_date_key"] = to_date_key(fact["order_approved_at"])
    fact["delivered_carrier_date_key"] = to_date_key(
        fact["order_delivered_carrier_date"]
    )
    fact["delivered_customer_date_key"] = to_date_key(
        fact["order_delivered_customer_date"]
    )
    fact["estimated_delivery_date_key"] = to_date_key(
        fact["order_estimated_delivery_date"]
    )

    fact["delivery_days"] = (
        fact["order_delivered_customer_date"] - fact["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    fact["shipping_delay_days"] = (
        fact["order_delivered_customer_date"] - fact["order_estimated_delivery_date"]
    ).dt.total_seconds() / 86400

    order_item_totals = fact.groupby("order_id")["item_total_value"].transform("sum")
    order_item_counts = fact.groupby("order_id")["order_item_id"].transform("count")
    fact["payment_value_total"] = fact["payment_value_total"].fillna(0)

    fact["allocated_payment_value"] = fact["payment_value_total"] / order_item_counts
    has_positive_item_total = order_item_totals > 0
    fact.loc[has_positive_item_total, "allocated_payment_value"] = (
        fact.loc[has_positive_item_total, "payment_value_total"]
        * fact.loc[has_positive_item_total, "item_total_value"]
        / order_item_totals.loc[has_positive_item_total]
    )

    fact["quantity"] = 1
    fact["delivery_days"] = fact["delivery_days"].round(2)
    fact["shipping_delay_days"] = fact["shipping_delay_days"].round(2)
    fact["price"] = fact["price"].round(2)
    fact["freight_value"] = fact["freight_value"].round(2)
    fact["item_total_value"] = fact["item_total_value"].round(2)
    fact["payment_value_total"] = fact["payment_value_total"].round(2)
    fact["allocated_payment_value"] = fact["allocated_payment_value"].round(2)

    fact = fact.sort_values(["order_id", "order_item_id", "product_id"]).reset_index(
        drop=True
    )
    fact.insert(0, "order_item_key", range(1, len(fact) + 1))

    columns = [
        "order_item_key",
        "order_id",
        "order_item_id",
        "customer_id",
        "seller_id",
        "product_id",
        "payment_id",
        "review_key",
        "review_id",
        "purchase_date_key",
        "approved_date_key",
        "delivered_carrier_date_key",
        "delivered_customer_date_key",
        "estimated_delivery_date_key",
        "order_status",
        "dominant_payment_type",
        "quantity",
        "price",
        "freight_value",
        "item_total_value",
        "payment_value_total",
        "allocated_payment_value",
        "delivery_days",
        "shipping_delay_days",
        "review_score",
    ]

    return fact[columns]


def write_table(df, output_dir, filename):
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / filename
    df.to_csv(path, index=False, encoding="utf-8")
    print(f"Wrote {path} ({len(df):,} rows)")


def transform(raw_dir = RAW_DIR, output_dir = WAREHOUSE_DIR):
    tables = load_raw_tables(raw_dir)

    dim_customer = build_dim_customer(tables["customers"])
    dim_seller = build_dim_seller(tables["sellers"])
    dim_product = build_dim_product(
        tables["products"], tables.get("category_translation")
    )
    dim_payment = build_dim_payment(tables["payments"])
    dim_review = build_dim_review(tables["reviews"])

    orders = tables["orders"].copy()
    for column in ORDER_DATE_COLUMNS:
        orders[column] = to_datetime(orders[column])

    dim_date = build_dim_date(
        orders["order_purchase_timestamp"],
        orders["order_approved_at"],
        orders["order_delivered_carrier_date"],
        orders["order_delivered_customer_date"],
        orders["order_estimated_delivery_date"],
        dim_review["review_creation_date"],
        dim_review["review_answer_timestamp"],
    )

    fact_orders = build_fact_orders(
        tables["orders"], tables["order_items"], dim_payment, dim_review
    )

    outputs = {
        "dim_customer": dim_customer,
        "dim_seller": dim_seller,
        "dim_product": dim_product,
        "dim_date": dim_date,
        "dim_payment": dim_payment,
        "dim_review": dim_review,
        "fact_orders": fact_orders,
    }

    for table_name, df in outputs.items():
        write_table(df, output_dir, WAREHOUSE_FILES[table_name])

    return outputs


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-dir",
        type=Path,
        default=RAW_DIR,
        help="Thư mục chứa file nguồn (CSV raw)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=WAREHOUSE_DIR,
        help="Đường dẫn lưu file dim và fact của star schema",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    transform(args.raw_dir, args.output_dir)

