#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

usage() {
    echo "Usage: $0 <number_of_workers>"
    echo "Example: $0 4"
    exit 1
}

if [ -z "$1" ]; then
    usage
fi

NUM_WORKERS=$1

# Validate input
if ! [[ "$NUM_WORKERS" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}Error: Number of workers must be a positive integer${NC}"
    exit 1
fi

if [ "$NUM_WORKERS" -lt 0 ] || [ "$NUM_WORKERS" -gt 20 ]; then
    echo -e "${RED}Error: Number of workers must be between 0 and 20${NC}"
    exit 1
fi

echo -e "${YELLOW}Scaling workers to $NUM_WORKERS instances...${NC}"

# Check if workers profile is active
if ! $DOCKER_COMPOSE -p $PROJECT_NAME ps | grep -q worker; then
    echo -e "${YELLOW}Workers not running. Starting worker profile...${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME --profile workers up -d --scale worker=$NUM_WORKERS
else
    $DOCKER_COMPOSE -p $PROJECT_NAME up -d --scale worker=$NUM_WORKERS --no-recreate
fi

echo
echo -e "${GREEN}✓ Workers scaled successfully${NC}"
echo

# Show worker status
echo -e "${YELLOW}Worker status:${NC}"
$DOCKER_COMPOSE -p $PROJECT_NAME ps worker

echo
echo "Monitor worker logs: make logs service=worker"