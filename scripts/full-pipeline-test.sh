#!/bin/bash

# scripts/full-pipeline-test.sh

set -e

PROJECT_NAME="trading_bot"
API_PORT=8010

echo "╔════════════════════════════════════════════════════════════╗"
echo "║         FULL PIPELINE TEST - End to End                    ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo

# Configuration
RUN_ID=10
INSTRUMENT_ID=643
START_DATE="2023-01-02"
END_DATE="2023-01-20"

echo "Test Configuration:"
echo "  Run ID: $RUN_ID"
echo "  Instrument: $INSTRUMENT_ID"
echo "  Date: $START_DATE"
echo

# Step 1: Migration
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 1: Data Migration (PostgreSQL → Parquet)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

MIGRATION_RESPONSE=$(curl -s -X POST http://localhost:$API_PORT/jobs/migrate \
  -H "Content-Type: application/json" \
  -d "{
    \"run_id\": $RUN_ID,
    \"instrument_id\": $INSTRUMENT_ID,
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"chunk_size\": 100000
  }")

MIGRATION_JOB_ID=$(echo $MIGRATION_RESPONSE | jq -r '.job_id')
echo "✓ Migration job created: $MIGRATION_JOB_ID"

# Wait for migration to complete
echo -n "Waiting for migration"
for i in {1..30}; do
    STATUS=$(curl -s http://localhost:$API_PORT/jobs/$MIGRATION_JOB_ID | jq -r '.status')
    if [ "$STATUS" == "completed" ]; then
        echo " ✓ Done!"
        break
    elif [ "$STATUS" == "failed" ]; then
        echo " ✗ Failed!"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo

# Step 2: Validate Parquet
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 2: Validate Parquet Data"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python scripts/validate-parquet.py data/parquet/RUN${RUN_ID}_INST${INSTRUMENT_ID} | head -20
echo

# Step 3: Backtest
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 3: Run Backtest"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

BACKTEST_RESPONSE=$(curl -s -X POST http://localhost:$API_PORT/jobs/backtest \
  -H "Content-Type: application/json" \
  -d "{
    \"strategy_name\": \"mean_reversion_nw\",
    \"run_id\": $RUN_ID,
    \"instrument_id\": $INSTRUMENT_ID,
    \"start_date\": \"$START_DATE\",
    \"end_date\": \"$END_DATE\",
    \"config\": {
      \"nw_bandwidth\": 20,
      \"nw_std\": 2.0
    }
  }")

BACKTEST_JOB_ID=$(echo $BACKTEST_RESPONSE | jq -r '.job_id')
echo "✓ Backtest job created: $BACKTEST_JOB_ID"

# Wait for backtest to complete
echo -n "Waiting for backtest"
for i in {1..30}; do
    STATUS=$(curl -s http://localhost:$API_PORT/jobs/$BACKTEST_JOB_ID | jq -r '.status')
    if [ "$STATUS" == "completed" ]; then
        echo " ✓ Done!"
        break
    elif [ "$STATUS" == "failed" ]; then
        echo " ✗ Failed!"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo

# Step 4: Results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Step 4: Backtest Results"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python scripts/validate-backtest.py $BACKTEST_JOB_ID

echo
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   ✅ ALL TESTS PASSED!                     ║"
echo "╚═════════.═══════════════════════════════════════════════════╝"