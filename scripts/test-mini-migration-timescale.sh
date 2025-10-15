#!/bin/bash

PROJECT_NAME="trading_bot"

echo "=== Mini Migration Test (TimescaleDB) ==="
echo

# Test with your known data
RUN_ID=24
INSTRUMENT_ID=651
START_DATE="2023-01-02"
END_DATE="2023-01-02"

echo "Testing with:"
echo "  Run ID: $RUN_ID"
echo "  Instrument ID: $INSTRUMENT_ID"
echo "  Date: $START_DATE"
echo

# Start data pipeline
echo "Starting data pipeline..."
docker compose -p $PROJECT_NAME --profile pipeline up -d
sleep 3

# Submit migration job
echo "Submitting migration job..."
RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/migrate \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": $RUN_ID,
    \"instrument_id\": $INSTRUMENT_ID,
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"chunk_size\": 10000
  }")

if command -v jq &> /dev/null; then
    JOB_ID=$(echo $RESPONSE | jq -r '.job_id')
    echo "Job created: $JOB_ID"
else
    echo "Response: $RESPONSE"
fi

echo
echo "Monitor with:"
echo "  make logs service=data_pipeline"
echo "  curl http://localhost:8000/jobs/\$JOB_ID | jq"
echo
echo "Check results:"
echo "  ls -lh data/parquet/"
echo "  tree data/parquet/"