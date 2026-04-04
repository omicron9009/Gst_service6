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
# Create Tables (SAFE)
# =========================
echo "📊 Checking tables..."

TABLES_EXIST=$(PGPASSWORD=${POSTGRES_PASSWORD} psql -U ${POSTGRES_USER} -h localhost -d ${POSTGRES_DB} -tAc \
"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='clients';")

if [ "$TABLES_EXIST" = "1" ]; then
  echo "✔ Tables exist — skipping"
else
  echo "🛠 Creating tables..."
  python - <<EOF
from sqlalchemy import create_engine
from database import Base

engine = create_engine("postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@localhost:5432/${POSTGRES_DB}")
Base.metadata.create_all(engine)
engine.dispose()
print("Tables created successfully.")
EOF
fi

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