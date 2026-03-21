#!/usr/bin/env python3
"""
GST Dev Console — DB Proxy
==========================
Tiny HTTP server that sits between your browser and your Postgres/MySQL DB.
The HTML file sends SQL to this proxy, which executes it and returns JSON.

INSTALL DEPS (pick your DB):
  pip install psycopg2-binary          # PostgreSQL
  pip install pymysql                  # MySQL / MariaDB

RUN:
  python db_proxy.py --conn "postgresql://user:pass@localhost:5432/mydb"
  python db_proxy.py --conn "mysql://user:pass@localhost:3306/mydb"
  python db_proxy.py --conn "postgresql://..." --port 5050  # custom port

Then open gst-api-tester.html and set the DB Proxy URL to:
  http://localhost:5000   (or whatever --port you chose)
"""

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse

# ── arg parse ──────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="GST Dev Console DB Proxy")
parser.add_argument("--conn", required=True,
                    help="Connection string: postgresql://user:pass@host:port/db  OR  mysql://user:pass@host:port/db")
parser.add_argument("--port", type=int, default=5000,
                    help="Port to listen on (default: 5000)")
parser.add_argument("--readonly", action="store_true", default=False,
                    help="Block INSERT/UPDATE/DELETE/DROP/TRUNCATE statements")
parser.add_argument("--allow-origin", default="*",
                    help="CORS origin to allow (default: *)")
args = parser.parse_args()

# ── detect DB type ─────────────────────────────────────────────────────────
conn_str = args.conn
db_type = None
if conn_str.startswith("postgresql://") or conn_str.startswith("postgres://"):
    db_type = "postgres"
elif conn_str.startswith("mysql://"):
    db_type = "mysql"
else:
    print("❌  Connection string must start with postgresql:// or mysql://")
    sys.exit(1)

# ── import driver ──────────────────────────────────────────────────────────
if db_type == "postgres":
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("❌  psycopg2 not found. Run:  pip install psycopg2-binary")
        sys.exit(1)
else:
    try:
        import pymysql
        import pymysql.cursors
    except ImportError:
        print("❌  pymysql not found. Run:  pip install pymysql")
        sys.exit(1)

# ── readonly guard ─────────────────────────────────────────────────────────
WRITE_KEYWORDS = {"insert", "update", "delete", "drop", "truncate", "alter", "create", "replace"}

def is_write_query(sql: str) -> bool:
    first = sql.strip().split()[0].lower() if sql.strip() else ""
    return first in WRITE_KEYWORDS

# ── DB helpers ─────────────────────────────────────────────────────────────
def get_connection():
    if db_type == "postgres":
        return psycopg2.connect(conn_str)
    else:
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
                    rows = [dict(r) for r in cur.fetchall()]
                    cols = list(rows[0].keys()) if rows else (
                        [desc[0] for desc in cur.description] if cur.description else []
                    )
                except Exception:
                    rows = []
                    cols = []
                conn.commit()
                return cols, rows, cur.rowcount
        else:
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

def list_tables():
    """Return list of table names."""
    if db_type == "postgres":
        sql = "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"
    else:
        sql = "SHOW TABLES;"
    cols, rows, _ = run_sql(sql)
    if not rows:
        return []
    key = list(rows[0].keys())[0]
    return [r[key] for r in rows]

def describe_table(table: str):
    """Return column info for a table."""
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

# ── JSON serialiser (handles dates, decimals, etc.) ─────────────────────────
import decimal, datetime

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

# ── HTTP handler ────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *a):
        print(f"  {self.command} {self.path} → {fmt % a}")

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

        elif path == "/db/tables":
            try:
                tables = list_tables()
                self.send_json(200, {"tables": tables, "count": len(tables)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        elif path.startswith("/db/describe/"):
            table = path[len("/db/describe/"):]
            try:
                cols, rows = describe_table(table)
                self.send_json(200, {"table": table, "columns": rows})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        elif path.startswith("/db/browse/"):
            table = path[len("/db/browse/"):]
            # parse limit/offset from query string
            from urllib.parse import parse_qs, urlparse as up
            qs = parse_qs(up(self.path).query)
            limit = int(qs.get("limit", ["200"])[0])
            offset = int(qs.get("offset", ["0"])[0])
            try:
                if db_type == "postgres":
                    sql = f'SELECT * FROM "{table}" LIMIT {limit} OFFSET {offset};'
                else:
                    sql = f"SELECT * FROM `{table}` LIMIT {limit} OFFSET {offset};"
                cols, rows, _ = run_sql(sql)
                self.send_json(200, {"table": table, "columns": cols, "rows": rows, "count": len(rows)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        else:
            self.send_json(404, {"error": "Not found", "endpoints": [
                "GET  /health",
                "GET  /db/tables",
                "GET  /db/browse/<table>?limit=200&offset=0",
                "GET  /db/describe/<table>",
                "POST /db/query   body: {\"sql\": \"SELECT ...\"}",
            ]})

    def do_POST(self):
        path = self.path.rstrip("/")

        if path == "/db/query":
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
                self.send_json(200, {
                    "ok": True,
                    "columns": cols,
                    "rows": rows,
                    "rowcount": rowcount,
                    "count": len(rows),
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})

        else:
            self.send_json(404, {"error": "Unknown POST endpoint"})


# ── main ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick connection test
    print(f"\n🔌  Testing connection to {db_type} DB…")
    try:
        tables = list_tables()
        print(f"✅  Connected! Found {len(tables)} tables: {', '.join(tables[:6])}{'…' if len(tables)>6 else ''}")
    except Exception as e:
        print(f"❌  Connection failed: {e}")
        sys.exit(1)

    print(f"\n🚀  DB Proxy running on http://localhost:{args.port}")
    print(f"    DB type  : {db_type}")
    print(f"    Readonly : {args.readonly}")
    print(f"    CORS     : {args.allow_origin}")
    print(f"\n    In gst-api-tester.html → DB tab → set proxy URL to:")
    print(f"    http://localhost:{args.port}\n")
    print("    Press Ctrl+C to stop.\n")

    server = HTTPServer(("localhost", args.port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋  Proxy stopped.")
