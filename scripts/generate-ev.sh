#!/bin/bash
# scripts/generate-env.sh
# Generate .env file with secure random passwords

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

generate_password() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

echo "=== Generate Environment Configuration ==="
echo

if [ -f .env ]; then
    echo -e "${YELLOW}Warning: .env file already exists${NC}"
    read -p "Overwrite? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Cancelled"
        exit 0
    fi
    # Backup existing
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
    echo "Existing .env backed up"
fi

echo "Generating secure passwords..."

POSTGRES_PASSWORD=$(generate_password)
REDIS_PASSWORD=$(generate_password)

cat > .env << EOF
# ============================================
# Trading Bot Project Configuration
# Generated: $(date)
# ============================================

# Project Settings
COMPOSE_PROJECT_NAME=trading_bot
PROJECT_VERSION=1.0.0
PYTHON_VERSION=3.12

# Network Configuration
NETWORK_SUBNET=172.28.0.0/16
NETWORK_GATEWAY=172.28.0.1

# PostgreSQL Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_HOST_PORT=5433
POSTGRES_DB=trading_data
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=$POSTGRES_PASSWORD

# PostgreSQL Performance Tuning
POSTGRES_SHARED_BUFFERS=2GB
POSTGRES_EFFECTIVE_CACHE_SIZE=8GB
POSTGRES_WORK_MEM=256MB
POSTGRES_MAINTENANCE_WORK_MEM=512MB
POSTGRES_MAX_CONNECTIONS=200

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_HOST_PORT=6380
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_MAXMEMORY=2gb

# Data Paths
DATA_ROOT=./data
PARQUET_PATH=./data/parquet
RESULTS_PATH=./data/results
LOGS_PATH=./data/logs

# Processing Configuration
CHUNK_SIZE=1000000
WORKER_CONCURRENCY=4
WORKER_REPLICAS=2

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_HOST_PORT=8000
API_WORKERS=2

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Development Mode
DEV_MODE=false
RELOAD=false
DEBUG=false

# Timezone
TZ=UTC
EOF

chmod 600 .env

echo -e "${GREEN}✓ .env file generated successfully${NC}"
echo
echo "Generated passwords:"
echo "  PostgreSQL: $POSTGRES_PASSWORD"
echo "  Redis: $REDIS_PASSWORD"
echo
echo -e "${YELLOW}⚠ Save these passwords securely!${NC}"
echo "The .env file has been created with secure permissions (600)"