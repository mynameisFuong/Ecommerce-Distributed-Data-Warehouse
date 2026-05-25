DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'readonly_user') THEN
        CREATE ROLE readonly_user LOGIN PASSWORD 'Readonly@2026!';
    ELSE
        ALTER ROLE readonly_user LOGIN PASSWORD 'Readonly@2026!';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'dashboard_user') THEN
        CREATE ROLE dashboard_user LOGIN PASSWORD 'Dashboard@2026!';
    ELSE
        ALTER ROLE dashboard_user LOGIN PASSWORD 'Dashboard@2026!';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_user') THEN
        CREATE ROLE etl_user LOGIN PASSWORD 'EtlLoad@2026!';
    ELSE
        ALTER ROLE etl_user LOGIN PASSWORD 'EtlLoad@2026!';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE ecommerce_dw TO readonly_user, dashboard_user, etl_user;
GRANT USAGE ON SCHEMA ecommerce_dw TO readonly_user, dashboard_user, etl_user;

GRANT SELECT ON ALL TABLES IN SCHEMA ecommerce_dw TO readonly_user, dashboard_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ecommerce_dw
GRANT SELECT ON TABLES TO readonly_user, dashboard_user;

GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA ecommerce_dw TO etl_user;
GRANT CREATE ON SCHEMA ecommerce_dw TO etl_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA ecommerce_dw
GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON TABLES TO etl_user;