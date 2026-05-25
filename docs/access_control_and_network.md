# Access Control and Network Access

## Database roles

| Role | Password | Purpose | Permissions |
|---|---|---|---|
| `readonly_user` | `Readonly@2026!` | External users / simple data access | `SELECT` only |
| `dashboard_user` | `Dashboard@2026!` | PowerBI / Metabase dashboard | `SELECT` only |
| `etl_user` | `EtlLoad@2026!` | ETL pipeline user | `SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `CREATE` on warehouse schema |
| `postgres` | `postgres` | Admin only | Superuser/admin |

Do not share `postgres/postgres` with external users.

## Connection endpoint

Only the Citus coordinator is exposed to the host machine.

```text
host: 192.168.100.192
port: 15432
database: ecommerce_dw
```

Workers are not exposed to external devices. Client tools should connect only to the coordinator.

## Example connection for another device in the same LAN

```text
host: 192.168.100.192
port: 15432
database: ecommerce_dw
username: readonly_user
password: Readonly@2026!
```

Test query:

```sql
SELECT COUNT(*)
FROM ecommerce_dw.fact_olist_orders;
```

Expected result:

```text
112650
```

## Security notes

The coordinator has been configured to require password authentication for network connections. Password authentication was tested successfully:

- Correct password for `readonly_user`: query returns `112650` rows.
- Wrong password for `readonly_user`: connection is rejected.
- `readonly_user` cannot create tables in `ecommerce_dw`.

## Windows Firewall

The coordinator listens on `192.168.100.192:15432`, but Windows Firewall must allow inbound TCP traffic on port `15432`.

Run PowerShell as Administrator and execute:

```powershell
New-NetFirewallRule `
  -DisplayName "Ecommerce Citus Coordinator 15432" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 15432 `
  -Profile Private,Domain
```

Check the port locally:

```powershell
Test-NetConnection -ComputerName 192.168.100.192 -Port 15432
```

## Access from outside the LAN

If the client device is not in the same network, one of these is required:

1. Deploy this Docker Compose project to a cloud VM/VPS and expose only the coordinator port.
2. Configure router port forwarding from a public IP to `192.168.100.192:15432`.
3. Use a private VPN solution such as Tailscale/WireGuard and connect through the VPN IP.

For a class demo, the safest options are cloud VM/VPS or VPN. Public router port forwarding should be restricted by source IP and should not use the `postgres` superuser.