#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Trading Bot Backup Script ==="
echo

# Check if services are running
if ! $DOCKER_COMPOSE -p $PROJECT_NAME ps | grep -q "postgres.*Up"; then
    echo -e "${RED}Error: Services are not running. Start with 'make start'${NC}"
    exit 1
fi

echo -e "${GREEN}Creating backup directory: $BACKUP_DIR${NC}"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
echo -e "${YELLOW}Backing up PostgreSQL...${NC}"
if $DOCKER_COMPOSE -p $PROJECT_NAME exec -T postgres pg_dump -U trading_user trading_data | gzip > $BACKUP_DIR/postgres_backup.sql.gz; then
    echo -e "${GREEN}✓ PostgreSQL backup complete${NC}"
else
    echo -e "${RED}✗ PostgreSQL backup failed${NC}"
fi

# Backup Redis
echo -e "${YELLOW}Backing up Redis...${NC}"
if $DOCKER_COMPOSE -p $PROJECT_NAME exec -T redis redis-cli SAVE > /dev/null 2>&1; then
    docker cp ${PROJECT_NAME}_redis:/data/dump.rdb $BACKUP_DIR/redis_backup.rdb
    echo -e "${GREEN}✓ Redis backup complete${NC}"
else
    echo -e "${RED}✗ Redis backup failed${NC}"
fi

# Backup configurations
echo -e "${YELLOW}Backing up configurations...${NC}"
cp .env $BACKUP_DIR/ 2>/dev/null || echo "No .env file found"
cp docker-compose.yml $BACKUP_DIR/
cp -r config $BACKUP_DIR/ 2>/dev/null || echo "No config directory found"
echo -e "${GREEN}✓ Configuration backup complete${NC}"

# Create backup info
cat > $BACKUP_DIR/backup_info.txt << EOF
Backup Created: $(date)
Project: $PROJECT_NAME
Docker Compose Version: $(docker compose version --short)
EOF

# Calculate sizes
echo
echo -e "${GREEN}Backup Summary:${NC}"
echo "Location: $BACKUP_DIR"
du -sh $BACKUP_DIR/*
echo
echo "Total size: $(du -sh $BACKUP_DIR | cut -f1)"
echo

echo -e "${GREEN}✓ Backup complete!${NC}"
echo
echo "To restore:"
echo "  PostgreSQL: gunzip < $BACKUP_DIR/postgres_backup.sql.gz | docker compose -p $PROJECT_NAME exec -T postgres psql -U trading_user trading_data"
echo "  Redis: docker cp $BACKUP_DIR/redis_backup.rdb ${PROJECT_NAME}_redis:/data/dump.rdb && docker compose -p $PROJECT_NAME restart redis"