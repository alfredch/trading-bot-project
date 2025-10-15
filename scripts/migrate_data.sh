#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Data Migration Script ==="
echo

# Check if services are running
if ! $DOCKER_COMPOSE -p $PROJECT_NAME ps | grep -q "postgres.*Up"; then
    echo -e "${YELLOW}PostgreSQL is not running. Starting services...${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME up -d postgres redis api
    echo "Waiting for services to be ready..."
    sleep 15
fi

# Get instrument from user
read -p "Enter instrument (e.g., ES.FUT): " INSTRUMENT
read -p "Enter start date (YYYY-MM-DD): " START_DATE
read -p "Enter end date (YYYY-MM-DD): " END_DATE

echo
echo "Starting migration for:"
echo "  Instrument: $INSTRUMENT"
echo "  Period: $START_DATE to $END_DATE"
echo

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq is not installed. Install with: sudo apt-get install jq${NC}"
    echo "Continuing without pretty JSON formatting..."
    JQ_CMD="cat"
else
    JQ_CMD="jq -r"
fi

# Submit job via API
echo "Submitting migration job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/migrate \
  -H "Content-Type: application/json" \
  -d "{
    \"instrument\": \"$INSTRUMENT\",
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\"
  }")

if command -v jq &> /dev/null; then
    JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
else
    JOB_ID=$(echo $JOB_RESPONSE | grep -oP '"job_id":"\K[^"]+')
fi

if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
    echo -e "${RED}Error: Failed to create migration job${NC}"
    echo $JOB_RESPONSE
    exit 1
fi

echo -e "${GREEN}Migration job created: $JOB_ID${NC}"
echo

# Start data pipeline worker
echo "Starting data pipeline worker..."
$DOCKER_COMPOSE -p $PROJECT_NAME --profile pipeline up -d data_pipeline

echo
echo "Monitoring progress (Ctrl+C to stop monitoring, job will continue)..."
echo

# Monitor job progress
while true; do
    STATUS_RESPONSE=$(curl -s http://localhost:8000/jobs/$JOB_ID)

    if command -v jq &> /dev/null; then
        STATUS=$(echo $STATUS_RESPONSE | jq -r '.status')
        PROGRESS=$(echo $STATUS_RESPONSE | jq -r '.progress')
        MESSAGE=$(echo $STATUS_RESPONSE | jq -r '.message')
    else
        STATUS=$(echo $STATUS_RESPONSE | grep -oP '"status":"\K[^"]+')
        PROGRESS=$(echo $STATUS_RESPONSE | grep -oP '"progress":\K[0-9]+')
        MESSAGE=$(echo $STATUS_RESPONSE | grep -oP '"message":"\K[^"]+')
    fi

    # Color status
    case $STATUS in
        running)
            STATUS_COLOR="${YELLOW}"
            ;;
        completed)
            STATUS_COLOR="${GREEN}"
            ;;
        failed)
            STATUS_COLOR="${RED}"
            ;;
        *)
            STATUS_COLOR="${NC}"
            ;;
    esac

    echo -ne "\r${STATUS_COLOR}Status: $STATUS${NC} | Progress: $PROGRESS% | $MESSAGE                    "

    if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
        echo
        break
    fi

    sleep 5
done

echo
if [ "$STATUS" == "completed" ]; then
    echo -e "${GREEN}✓ Migration completed successfully!${NC}"
    echo
    echo "View results:"
    echo "  ls -lh data/parquet/$INSTRUMENT/"
else
    echo -e "${RED}✗ Migration failed.${NC}"
    echo "Check logs: make logs service=data_pipeline"
    exit 1
fi