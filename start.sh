#!/bin/bash

# 1. Configure PostgreSQL to accept connections from any IP
PG_CONF=$(find /etc/postgresql -name postgresql.conf | head -1)
PG_HBA=$(find /etc/postgresql -name pg_hba.conf | head -1)

# Listen on all interfaces, not just localhost
sed -i "s/^#\?listen_addresses\s*=.*/listen_addresses = '*'/" "$PG_CONF"

# Rewrite pg_hba.conf: trust local (unix socket) so we can set the password,
# md5 for all TCP connections (localhost + remote).
cat > "$PG_HBA" <<'EOF'
local   all   all                   trust
host    all   all   127.0.0.1/32    md5
host    all   all   ::1/128         md5
host    all   all   0.0.0.0/0       md5
EOF

echo "Starting PostgreSQL Database..."
service postgresql start

# Wait for PostgreSQL to be available
until su - postgres -c "psql -c '\q'"; do
  echo "Waiting for postgres..."
  sleep 1
done

# 2. Provision Database and User (matches the default string in your config.py)
echo "Configuring Database User and Schema..."
su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD 'root';\""
su - postgres -c "psql -c \"CREATE DATABASE gst_dash_test;\"" || true

# Reload pg_hba so password auth is enforced for all connections going forward
su - postgres -c "psql -c \"SELECT pg_reload_conf();\""

# Export the DB URL so the Python scripts pick up the local instance
export DATABASE_URL="postgresql+asyncpg://postgres:root@localhost:5432/gst_dash_test"

# 2b. Create SQLAlchemy tables ONLY if they don't already exist
echo "Checking if database tables exist..."
TABLES_EXIST=$(PGPASSWORD=root psql -U postgres -h localhost -d gst_dash_test -tAc \
  "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public' AND table_name='clients';")

if [ "$TABLES_EXIST" = "1" ]; then
  echo "Tables already exist — skipping creation to preserve data."
else
  echo "Tables not found — creating database tables..."
  python -c "
from sqlalchemy import create_engine
from database import Base          # imports Base with all models registered
sync_url = 'postgresql://postgres:root@localhost:5432/gst_dash_test'
eng = create_engine(sync_url)
Base.metadata.create_all(eng)
eng.dispose()
print('All tables created successfully.')
"
fi

# 3. Start DB Proxy in the background
echo "Starting DB Proxy on port 8050..."
uvicorn db_proxy.main:app --host 0.0.0.0 --port 8050 &

# 4. Start Main Service API in the background
echo "Starting Service API on port 8000..."
uvicorn main:app --host 0.0.0.0 --port 8000 &

# 5. Start Frontend React app in the background
echo "Starting Frontend on port 8080..."
cd gst-navigator-pro-main && npm run dev -- --host 0.0.0.0 --port 8080 &

# Wait on the background processes
wait -n

exit $?
