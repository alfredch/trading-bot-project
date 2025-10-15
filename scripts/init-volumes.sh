#!/bin/bash
# scripts/init-volumes.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Initializing Docker Volumes ==="
echo

# Create volume directories
echo -e "${YELLOW}Creating volume directories...${NC}"
mkdir -p data/volumes/postgres
mkdir -p data/volumes/redis

# Set ownership (for bind mounts)
echo -e "${YELLOW}Setting ownership...${NC}"
# PostgreSQL needs specific UID
sudo chown -R 999:999 data/volumes/postgres 2>/dev/null || true
# Redis needs specific UID
sudo chown -R 999:999 data/volumes/redis 2>/dev/null || true

echo -e "${GREEN}✓ Volume directories initialized${NC}"
echo
echo "Note: If permission errors occur, run with sudo"