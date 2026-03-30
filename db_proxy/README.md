# DB Proxy

Standalone FastAPI app for read-only database export across the GST business tables.

Run:

```bash
uvicorn db_proxy.main:app --host 127.0.0.1 --port 8050
```

Or:

```bash
python -m db_proxy.main
```

Basic auth env vars:

```bash
DB_PROXY_BASIC_AUTH_USERNAME=proxy_admin
DB_PROXY_BASIC_AUTH_PASSWORD=change-me
```

Route:

```text
GET /fetch
```

Supported query params:

- `gstin=...` repeatable
- `client_id=...` repeatable
- `include_inactive=true|false`
- `tables=...` repeatable
