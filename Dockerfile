# Use Python 3.11 slim as the base image
FROM python:3.11-slim

# Install system dependencies, Node.js, AND PostgreSQL
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y curl sudo postgresql postgresql-contrib \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies natively
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" sqlalchemy asyncpg requests pydantic python-dotenv python-multipart

# Copy package.json and install Node dependencies for frontend
COPY gst-navigator-pro-main/package*.json ./gst-navigator-pro-main/
RUN cd gst-navigator-pro-main && npm ci

# Copy the rest of the application
COPY . .

# Make the start script executable
RUN chmod +x /app/start.sh

# Expose ports: API (8000), DB Proxy (8050), Frontend (8080), and DB (5432)
EXPOSE 8000 8050 8080 5432

# Run the unified boot script
CMD ["/app/start.sh"]
