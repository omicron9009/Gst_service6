#!/bin/bash
set -e

echo "🚀 Starting GST Service Stack..."

# =========================
# ENV VARIABLES
# =========================
POSTGRES_USER=${POSTGRES_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-root}
POSTGRES_DB=${POSTGRES_DB:-gst_dash_test}
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Only set DATABASE_URL if not already provided (e.g. via --env-file)
export DATABASE_URL="${DATABASE_URL:-postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}}"

# =========================
# Locate PostgreSQL configs
# =========================
PG_CONF=$(find /etc/postgresql -name postgresql.conf | head -1)
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)

echo "⚙️ Configuring PostgreSQL..."

# 🔒 Listen on all interfaces so mapped port 5432 works for external tools
sed -i "s/^#\?listen_addresses\s*=.*/listen_addresses = '*'/" "$PG_CONF"

# 🔒 Secure auth config (md5 for all connections)
cat > "$PG_HBA" <<EOF
local   all   all                   peer
host    all   all   127.0.0.1/32    md5
host    all   all   ::1/128         md5
host    all   all   0.0.0.0/0       md5
EOF

# =========================
# Start PostgreSQL
# =========================
echo "🟢 Starting PostgreSQL..."

pg_ctlcluster $(ls /etc/postgresql) main start

# Wait for DB ready
until pg_isready -h localhost -p 5432 > /dev/null 2>&1; do
  echo "⏳ Waiting for postgres..."
  sleep 1
done

echo "✅ PostgreSQL Ready"

# =========================
# Setup DB + USER
# =========================
echo "🧱 Setting up database..."

# Set password
su - postgres -c "psql -tc \"ALTER USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';\"" || true

# Create DB if not exists
su - postgres -c "psql -tc \"SELECT 1 FROM pg_database WHERE datname='${POSTGRES_DB}'\"" | grep -q 1 || \
su - postgres -c "createdb ${POSTGRES_DB}"

# Reload config
su - postgres -c "psql -c \"SELECT pg_reload_conf();\""

# =========================
# Create Tables + Auto-Migrate (SAFE)
# =========================
echo "📊 Creating tables & migrating missing columns..."

python - <<'PYEOF'
import os, sys
from sqlalchemy import create_engine, inspect, text

# --- import every model so Base.metadata knows about all tables ---
from database import Base

DB_URL = os.environ["DATABASE_URL"].replace("+asyncpg", "")
engine = create_engine(DB_URL)

# 1) Create any brand-new tables (no-op for existing ones)
Base.metadata.create_all(engine)
print("✔ create_all done")

# 2) Auto-add missing columns to existing tables
inspector = inspect(engine)
existing_tables = set(inspector.get_table_names(schema="public"))

with engine.begin() as conn:
    for table in Base.metadata.sorted_tables:
        if table.name not in existing_tables:
            continue                       # just created above, nothing to migrate
        db_cols = {c["name"] for c in inspector.get_columns(table.name, schema="public")}
        for col in table.columns:
            if col.name in db_cols:
                continue                   # already present
            # Build the column type DDL
            col_type = col.type.compile(dialect=engine.dialect)
            nullable = "" if col.nullable else " NOT NULL"
            default  = ""
            if col.server_default is not None:
                sd = col.server_default.arg
                default = f" DEFAULT {sd.text}" if hasattr(sd, "text") else f" DEFAULT {sd.compile(dialect=engine.dialect)}"
            ddl = f'ALTER TABLE "{table.name}" ADD COLUMN "{col.name}" {col_type}{nullable}{default};'
            print(f"  ➕ {ddl}")
            conn.execute(text(ddl))

engine.dispose()
print("✔ Migration complete")
PYEOF

# =========================
# Start Services
# =========================
echo "🚀 Starting services..."

uvicorn db_proxy.main:app --host 0.0.0.0 --port 8050 &
PID_PROXY=$!

uvicorn main:app --host 0.0.0.0 --port 8000 &
PID_API=$!

cd gst-navigator-pro-main
npm run dev -- --host 0.0.0.0 --port 8080 &
PID_FRONTEND=$!
cd ..

# =========================
# Monitor processes
# =========================
echo "👀 Monitoring services..."

wait -n $PID_PROXY $PID_API $PID_FRONTEND

echo "❌ One service exited. Stopping all..."
kill -TERM $PID_PROXY $PID_API $PID_FRONTEND 2>/dev/null

exit 1