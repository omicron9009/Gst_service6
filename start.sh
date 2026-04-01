#!/bin/bash

# 1. Start PostgreSQL Service
echo "Starting PostgreSQL Database..."
service postgresql start

# Wait for PostgreSQL to be available
until su - postgres -c "psql -c '\q'"; do
  echo "Waiting for postgres..."
  sleep 1
done

# 2. Provision Database and User (matches the default string in your config.py)
echo "Configuring Database User and Schema..."
su - postgres -c 'psql -c "ALTER USER postgres WITH PASSWORD ''root'';"'
su - postgres -c 'psql -c "CREATE DATABASE gst_dash_test;"' || true

# Export the DB URL so the Python scripts pick up the local instance
export DATABASE_URL="postgresql+asyncpg://postgres:root@localhost:5432/gst_dash_test"

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
