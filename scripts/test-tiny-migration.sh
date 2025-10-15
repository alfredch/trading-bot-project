#!/bin/bash
# scripts/test-tiny-migration.sh

PROJECT_NAME="trading_bot"

echo "=== TINY Migration Test (10,000 rows only) ==="
echo

# Use smallest dataset
RUN_ID=10
INSTRUMENT_ID=643
START_DATE="2023-01-02"
END_DATE="2023-01-02"  # Nur 1 Tag
CHUNK_SIZE=10000

echo "Test Configuration:"
echo "  Run ID: $RUN_ID"
echo "  Instrument ID: $INSTRUMENT_ID"
echo "  Date: $START_DATE (single day)"
echo "  Chunk Size: $CHUNK_SIZE rows"
echo

# Check services
echo "Checking services..."
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo "❌ API not running. Start with: make start"
    exit 1
fi
echo "✅ API running"

# Start data pipeline
echo
echo "Starting data pipeline..."
docker compose -p $PROJECT_NAME --profile pipeline up -d
sleep 3

# Submit job
echo
echo "Submitting migration job..."
RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/migrate \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": $RUN_ID,
    \"instrument_id\": $INSTRUMENT_ID,
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"chunk_size\": $CHUNK_SIZE
  }")

# Pretty print if jq available, otherwise just echo
if command -v jq &> /dev/null; then
    echo "$RESPONSE" | jq '.'
    JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
else
    echo "$RESPONSE"
    JOB_ID=$(echo "$RESPONSE" | grep -oP '"job_id":"\K[^"]+')
fi

echo
echo "Job ID: $JOB_ID"
echo
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Monitor progress:"
echo "  curl -s http://localhost:8000/jobs/$JOB_ID | jq"
echo "  make logs service=data_pipeline"
echo
echo "Check results when done:"
echo "  ls -lh data/parquet/"
echo "  tree data/parquet/ -L 3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"