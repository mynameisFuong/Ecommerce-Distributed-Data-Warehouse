from __future__ import annotations

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"
RAW_DIR = f"{PROJECT_DIR}/data/raw"
WAREHOUSE_DIR = f"{PROJECT_DIR}/data/warehouse"
MANIFEST_PATH = f"{PROJECT_DIR}/data/processed/extract_manifest.json"

DEFAULT_ARGS = {
    "owner": "ecommerce_dw_team",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}

with DAG(
    dag_id="ecommerce_distributed_dw_etl",
    description="Extract, transform, and load Olist data into a distributed Citus data warehouse.",
    default_args=DEFAULT_ARGS,
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    tags=["ecommerce", "distributed-database", "citus", "data-warehouse"],
) as dag:
    extract_raw_files = BashOperator(
        task_id="extract_raw_files",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python etl/extract.py --raw-dir {RAW_DIR} --output-path {MANIFEST_PATH}"
        ),
    )

    transform_to_star_schema = BashOperator(
        task_id="transform_to_star_schema",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python etl/transform.py --raw-dir {RAW_DIR} --output-dir {WAREHOUSE_DIR}"
        ),
    )

    load_to_citus = BashOperator(
        task_id="load_to_citus",
        bash_command=(
            f"cd {PROJECT_DIR} && "
            f"python etl/load.py --warehouse-dir {WAREHOUSE_DIR}"
        ),
        env={
            "DW_HOST": "citus-coordinator",
            "DW_PORT": "5432",
            "DW_DATABASE": "ecommerce_dw",
            "DW_USER": "postgres",
            "DW_PASSWORD": "postgres",
            "PYTHONPATH": PROJECT_DIR,
        },
    )

    verify_warehouse = BashOperator(
        task_id="verify_warehouse",
        bash_command=(
            "python -c \""
            "import psycopg2; "
            "conn=psycopg2.connect(host='citus-coordinator', port=5432, "
            "dbname='ecommerce_dw', user='readonly_user', password='Readonly@2026!'); "
            "cur=conn.cursor(); "
            "cur.execute('SELECT COUNT(*) FROM ecommerce_dw.fact_olist_orders'); "
            "count=cur.fetchone()[0]; "
            "print(f'fact_olist_orders row count: {count}'); "
            "assert count == 112650; "
            "conn.close()"
            "\""
        ),
    )

    extract_raw_files >> transform_to_star_schema >> load_to_citus >> verify_warehouse