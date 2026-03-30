#!/usr/bin/env python3
"""
GST Dev Console - DB Proxy
==========================
Tiny HTTP server that sits between your browser and your Postgres/MySQL DB.
The HTML file sends SQL to this proxy, which executes it and returns JSON.

Install deps:
  pip install psycopg2-binary          # PostgreSQL
  pip install pymysql                  # MySQL / MariaDB

Run:
  python db_proxy.py --conn "postgresql+asyncpg://user:pass@localhost:5432/mydb"
  python db_proxy.py --conn "mysql://user:pass@localhost:3306/mydb"
  python db_proxy.py --conn "postgresql+asyncpg://..." --port 5050

Then open gst-api-tester.html and set the DB Proxy URL to:
  http://localhost:5000
"""

import argparse
import datetime
import decimal
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote, urlparse


parser = argparse.ArgumentParser(description="GST Dev Console DB Proxy")
parser.add_argument(
    "--conn",
    default=os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:root@localhost:5432/gst_dash_test",
    ),
    help="Connection string: postgresql+asyncpg://user:pass@host:port/db or mysql://user:pass@host:port/db",
)
parser.add_argument("--port", type=int, default=5000, help="Port to listen on (default: 5000)")
parser.add_argument(
    "--readonly",
    action="store_true",
    default=False,
    help="Block INSERT/UPDATE/DELETE/DROP/TRUNCATE statements",
)
parser.add_argument("--allow-origin", default="*", help="CORS origin to allow (default: *)")
args = parser.parse_args()

raw_conn_str = args.conn
conn_str = raw_conn_str
if conn_str.startswith("postgresql+asyncpg://"):
    conn_str = conn_str.replace("postgresql+asyncpg://", "postgresql://", 1)

if conn_str.startswith(("postgresql://", "postgres://")):
    db_type = "postgres"
elif conn_str.startswith("mysql://"):
    db_type = "mysql"
else:
    print("Connection string must start with postgresql+asyncpg://, postgresql://, postgres://, or mysql://")
    sys.exit(1)

if db_type == "postgres":
    try:
        import psycopg2
        import psycopg2.errors
        import psycopg2.extras
        import psycopg2.sql
    except ImportError:
        print("psycopg2 not found. Run: pip install psycopg2-binary")
        sys.exit(1)
else:
    try:
        import pymysql
        import pymysql.cursors
    except ImportError:
        print("pymysql not found. Run: pip install pymysql")
        sys.exit(1)


WRITE_KEYWORDS = {"insert", "update", "delete", "drop", "truncate", "alter", "create", "replace"}


def is_write_query(sql: str) -> bool:
    first = sql.strip().split()[0].lower() if sql.strip() else ""
    return first in WRITE_KEYWORDS


def postgres_connect_kwargs(database_name: str | None = None) -> dict[str, object]:
    parsed = urlparse(conn_str)
    kwargs: dict[str, object] = {
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "dbname": database_name or parsed.path.lstrip("/"),
    }
    if parsed.username is not None:
        kwargs["user"] = unquote(parsed.username)
    if parsed.password is not None:
        kwargs["password"] = unquote(parsed.password)
    return kwargs


def ensure_postgres_database_exists() -> bool:
    database_name = postgres_connect_kwargs()["dbname"]
    if not database_name:
        raise RuntimeError("PostgreSQL connection string must include a database name.")

    admin_targets: list[str] = []
    for candidate in (os.getenv("DATABASE_ADMIN_DB", "postgres"), "postgres", "template1"):
        if candidate and candidate not in admin_targets and candidate != database_name:
            admin_targets.append(candidate)

    last_error: Exception | None = None
    for admin_db in admin_targets:
        admin_conn = None
        try:
            admin_conn = psycopg2.connect(**postgres_connect_kwargs(admin_db))
            admin_conn.autocommit = True
            with admin_conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database_name,))
                if cur.fetchone():
                    return False
                cur.execute(
                    psycopg2.sql.SQL("CREATE DATABASE {}").format(
                        psycopg2.sql.Identifier(str(database_name))
                    )
                )
                return True
        except psycopg2.errors.DuplicateDatabase:
            return False
        except Exception as exc:
            last_error = exc
        finally:
            if admin_conn is not None:
                admin_conn.close()

    raise RuntimeError(
        f"Unable to connect to a PostgreSQL admin database ({', '.join(admin_targets)})."
    ) from last_error


def get_connection():
    if db_type == "postgres":
        return psycopg2.connect(**postgres_connect_kwargs())

    parsed = urlparse(conn_str)
    return pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip("/"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def run_sql(sql: str):
    """Execute SQL and return (columns, rows, rowcount)."""
    conn = get_connection()
    try:
        if db_type == "postgres":
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql)
                try:
                    rows = [dict(row) for row in cur.fetchall()]
                    cols = list(rows[0].keys()) if rows else (
                        [desc[0] for desc in cur.description] if cur.description else []
                    )
                except Exception:
                    rows = []
                    cols = []
                conn.commit()
                return cols, rows, cur.rowcount

        with conn.cursor() as cur:
            cur.execute(sql)
            try:
                rows = cur.fetchall() or []
                cols = list(rows[0].keys()) if rows else []
            except Exception:
                rows = []
                cols = []
            conn.commit()
            return cols, rows, cur.rowcount
    finally:
        conn.close()


def list_tables() -> list[str]:
    if db_type == "postgres":
        sql = (
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public' ORDER BY table_name;"
        )
    else:
        sql = "SHOW TABLES;"
    _, rows, _ = run_sql(sql)
    if not rows:
        return []
    key = list(rows[0].keys())[0]
    return [row[key] for row in rows]


def describe_table(table: str):
    if db_type == "postgres":
        sql = f"""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """
    else:
        sql = f"DESCRIBE `{table}`;"
    cols, rows, _ = run_sql(sql)
    return cols, rows


def json_default(obj):
    if isinstance(obj, (datetime.date, datetime.datetime)):
        return obj.isoformat()
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return str(obj)


def to_json(obj):
    return json.dumps(obj, default=json_default)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args_):
        print(f"  {self.command} {self.path} -> {fmt % args_}")

    def cors(self):
        self.send_header("Access-Control-Allow-Origin", args.allow_origin)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_json(self, code, obj):
        body = to_json(obj).encode()
        self.send_response(code)
        self.cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")

        if path == "/health":
            self.send_json(200, {"ok": True, "db": db_type, "readonly": args.readonly})
            return

        if path == "/db/tables":
            try:
                tables = list_tables()
                self.send_json(200, {"tables": tables, "count": len(tables)})
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if path.startswith("/db/describe/"):
            table = path[len("/db/describe/") :]
            try:
                _, rows = describe_table(table)
                self.send_json(200, {"table": table, "columns": rows})
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if path.startswith("/db/browse/"):
            from urllib.parse import parse_qs, urlparse as parse_url

            table = path[len("/db/browse/") :]
            qs = parse_qs(parse_url(self.path).query)
            limit = int(qs.get("limit", ["200"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            try:
                if db_type == "postgres":
                    sql = f'SELECT * FROM "{table}" LIMIT {limit} OFFSET {offset};'
                else:
                    sql = f"SELECT * FROM `{table}` LIMIT {limit} OFFSET {offset};"
                cols, rows, _ = run_sql(sql)
                self.send_json(200, {"table": table, "columns": cols, "rows": rows, "count": len(rows)})
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        self.send_json(
            404,
            {
                "error": "Not found",
                "endpoints": [
                    "GET  /health",
                    "GET  /db/tables",
                    "GET  /db/browse/<table>?limit=200&offset=0",
                    "GET  /db/describe/<table>",
                    "POST /db/query   body: {\"sql\": \"SELECT ...\"}",
                ],
            },
        )

    def do_POST(self):
        path = self.path.rstrip("/")

        if path != "/db/query":
            self.send_json(404, {"error": "Unknown POST endpoint"})
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            payload = json.loads(body)
        except Exception:
            self.send_json(400, {"error": "Invalid JSON body"})
            return

        sql = payload.get("sql", "").strip()
        if not sql:
            self.send_json(400, {"error": "Missing 'sql' field"})
            return

        if args.readonly and is_write_query(sql):
            self.send_json(403, {"error": "Write queries are blocked (--readonly mode)"})
            return

        try:
            cols, rows, rowcount = run_sql(sql)
            self.send_json(
                200,
                {
                    "ok": True,
                    "columns": cols,
                    "rows": rows,
                    "rowcount": rowcount,
                    "count": len(rows),
                },
            )
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})


if __name__ == "__main__":
    print(f"\nTesting connection to {db_type} DB...")
    try:
        if db_type == "postgres":
            created = ensure_postgres_database_exists()
            if created:
                print("Created missing PostgreSQL database before startup.")
        tables = list_tables()
        preview = ", ".join(tables[:6])
        suffix = "..." if len(tables) > 6 else ""
        print(f"Connected. Found {len(tables)} tables: {preview}{suffix}")
    except Exception as exc:
        print(f"Connection failed: {exc}")
        sys.exit(1)

    print(f"\nDB Proxy running on http://localhost:{args.port}")
    print(f"  DB type  : {db_type}")
    print(f"  Readonly : {args.readonly}")
    print(f"  CORS     : {args.allow_origin}")
    print(f"\nSet the proxy URL in gst-api-tester.html to http://localhost:{args.port}\n")

    server = HTTPServer(("localhost", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nProxy stopped.")
