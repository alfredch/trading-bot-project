#!/bin/bash
# scripts/test-worker.sh

PROJECT_NAME="trading_bot"

echo "=== Testing Worker Functionality ==="
echo

# Test 1: Submit test job
echo "Test 1: Submitting test migration job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "instrument": "TEST.FUT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-02",
    "chunk_size": 1000
  }')

JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
echo "Job created: $JOB_ID"
echo

# Test 2: Start worker
echo "Test 2: Starting worker..."
docker compose -p $PROJECT_NAME --profile workers up -d worker
sleep 5

# Test 3: Monitor job progress
echo "Test 3: Monitoring job progress..."
for i in {1..10}; do
    STATUS=$(curl -s http://localhost:8000/jobs/$JOB_ID | jq -r '.status')
    PROGRESS=$(curl -s http://localhost:8000/jobs/$JOB_ID | jq -r '.progress')
    echo "  Status: $STATUS, Progress: $PROGRESS%"

    if [ "$STATUS" == "completed" ] || [ "$STATUS" == "failed" ]; then
        break
    fi

    sleep 3
done

echo
echo "✓ Worker test complete"