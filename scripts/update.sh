#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Trading Bot Update Script ==="
echo

# Pull latest code
echo -e "${YELLOW}Pulling latest code...${NC}"
git pull

# Pull latest images
echo -e "${YELLOW}Pulling latest Docker images...${NC}"
$DOCKER_COMPOSE -p $PROJECT_NAME pull

# Rebuild images
echo -e "${YELLOW}Rebuilding custom images...${NC}"
$DOCKER_COMPOSE -p $PROJECT_NAME build

# Restart services
echo -e "${YELLOW}Restarting services...${NC}"
$DOCKER_COMPOSE -p $PROJECT_NAME up -d

echo
echo -e "${GREEN}✓ Update complete!${NC}"
echo
echo "Check status: make status"