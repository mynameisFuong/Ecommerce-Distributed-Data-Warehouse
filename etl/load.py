import argparse
import csv
import os
import time
from pathlib import Path

import psycopg2
from psycopg2 import sql

try:
    from .config import PROJECT_ROOT, WAREHOUSE_DIR, WAREHOUSE_FILES
except ImportError:
    from config import PROJECT_ROOT, WAREHOUSE_DIR, WAREHOUSE_FILES


SQL_DIR = PROJECT_ROOT / "sql"

TABLE_LOAD_ORDER = [
    ("dim_customer", "dim_customer"),
    ("dim_seller", "dim_seller"),
    ("dim_product", "dim_product"),
    ("dim_date", "dim_date"),
    ("dim_payment", "dim_payment"),
    ("dim_review", "dim_review"),
    ("fact_olist_orders", "fact_orders"),
]


def connect(args: argparse.Namespace):
    return psycopg2.connect(
        host=args.host,
        port=args.port,
        dbname=args.database,
        user=args.user,
        password=args.password,
        connect_timeout=10,
    )


def ensure_database(args: argparse.Namespace) -> None:
    connection = connect_with_retry(args, database="postgres")
    connection.autocommit = True

    try:
        with connection.cursor() as cursor:
            print(f"Checking database {args.database}...", flush=True)
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s;",
                (args.database,),
            )
            exists = cursor.fetchone() is not None
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {};").format(
                        sql.Identifier(args.database)
                    )
                )
                print(f"Created database {args.database}", flush=True)
            else:
                print(f"Database {args.database} already exists", flush=True)
    finally:
        connection.close()


def connect_with_retry(
    args: argparse.Namespace,
    database: str | None = None,
    retries: int = 20,
    delay_seconds: int = 3,
):
    dbname = database or args.database
    last_error = None

    for attempt in range(1, retries + 1):
        try:
            return psycopg2.connect(
                host=args.host,
                port=args.port,
                dbname=dbname,
                user=args.user,
                password=args.password,
                connect_timeout=10,
            )
        except psycopg2.OperationalError as error:
            last_error = error
            print(
                f"Waiting for PostgreSQL at {args.host}:{args.port}/{dbname} "
                f"({attempt}/{retries})...",
                flush=True,
            )
            time.sleep(delay_seconds)

    raise last_error


def run_sql_file(connection, path: Path) -> None:
    print(f"Executing {path}...", flush=True)
    sql_text = path.read_text(encoding="utf-8")
    with connection.cursor() as cursor:
        cursor.execute(sql_text)
    connection.commit()
    print(f"Executed {path}", flush=True)


def register_workers(connection, workers: list[str], worker_port: int) -> None:
    print("Registering Citus workers...", flush=True)
    with connection.cursor() as cursor:
        print("Creating Citus extension if needed...", flush=True)
        cursor.execute("CREATE EXTENSION IF NOT EXISTS citus;")
        for worker in workers:
            print(f"Registering worker {worker}:{worker_port}...", flush=True)
            cursor.execute(
                """
                SELECT citus_add_node(%s, %s)
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM pg_dist_node
                    WHERE nodename = %s
                      AND nodeport = %s
                );
                """,
                (worker, worker_port, worker, worker_port),
            )
        cursor.execute(
            """
            SELECT nodename, nodeport, isactive
            FROM pg_dist_node
            ORDER BY nodeid;
            """
        )
        rows = cursor.fetchall()
    connection.commit()

    print("Registered Citus workers:", flush=True)
    for nodename, nodeport, isactive in rows:
        print(f"- {nodename}:{nodeport} active={isactive}", flush=True)


def truncate_tables(connection) -> None:
    tables = ", ".join(
        [f"ecommerce_dw.{table_name}" for table_name, _ in reversed(TABLE_LOAD_ORDER)]
    )
    with connection.cursor() as cursor:
        cursor.execute(f"TRUNCATE TABLE {tables} CASCADE;")
    connection.commit()


def copy_csv(connection, table_name: str, csv_path: Path) -> None:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing warehouse CSV: {csv_path}")

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        header = next(csv.reader(file))

    column_list = sql.SQL(", ").join(sql.Identifier(column) for column in header)
    copy_sql = sql.SQL(
        """
        COPY ecommerce_dw.{} ({})
        FROM STDIN
        WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8');
        """
    ).format(sql.Identifier(table_name), column_list)

    with csv_path.open("r", encoding="utf-8", newline="") as file:
        with connection.cursor() as cursor:
            cursor.copy_expert(copy_sql.as_string(connection), file)
    connection.commit()
    print(f"Loaded {csv_path.name} into ecommerce_dw.{table_name}", flush=True)


def load_data(connection, warehouse_dir: Path) -> None:
    for table_name, file_key in TABLE_LOAD_ORDER:
        csv_path = warehouse_dir / WAREHOUSE_FILES[file_key]
        copy_csv(connection, table_name, csv_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the Citus warehouse schema and load transformed CSV files."
    )
    parser.add_argument("--host", default=os.getenv("DW_HOST", "127.0.0.1"))
    parser.add_argument("--port", default=int(os.getenv("DW_PORT", "15432")), type=int)
    parser.add_argument("--database", default=os.getenv("DW_DATABASE", "ecommerce_dw"))
    parser.add_argument("--user", default=os.getenv("DW_USER", "postgres"))
    parser.add_argument("--password", default=os.getenv("DW_PASSWORD", "postgres"))
    parser.add_argument(
        "--warehouse-dir",
        default=WAREHOUSE_DIR,
        type=Path,
        help="Directory that contains transformed warehouse CSV files.",
    )
    parser.add_argument(
        "--workers",
        default="citus-worker-1,citus-worker-2,citus-worker-3,citus-worker-4",
        help="Comma-separated Citus worker hostnames inside the Docker network.",
    )
    parser.add_argument("--worker-port", default=5432, type=int)
    parser.add_argument(
        "--skip-schema",
        action="store_true",
        help="Do not recreate schema/distributed tables before loading.",
    )
    parser.add_argument(
        "--skip-load",
        action="store_true",
        help="Create/register schema only; do not copy CSV files.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    workers = [worker.strip() for worker in args.workers.split(",") if worker.strip()]

    print(
        f"Loading warehouse to PostgreSQL/Citus at "
        f"{args.host}:{args.port}/{args.database}",
        flush=True,
    )
    ensure_database(args)

    print(f"Connecting to database {args.database}...", flush=True)
    with connect_with_retry(args) as connection:
        register_workers(connection, workers, args.worker_port)

        if not args.skip_schema:
            run_sql_file(connection, SQL_DIR / "01_create_schema.sql")
            run_sql_file(connection, SQL_DIR / "02_create_distributed_tables.sql")
        else:
            truncate_tables(connection)

        if not args.skip_load:
            load_data(connection, args.warehouse_dir)

        access_roles_sql = SQL_DIR / "06_create_access_roles.sql"
        if access_roles_sql.exists():
            run_sql_file(connection, access_roles_sql)


if __name__ == "__main__":
    main()
