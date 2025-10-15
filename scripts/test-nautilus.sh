#!/bin/bash
# scripts/test-nautilus.sh

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== Testing Nautilus Backtest Service ==="
echo

# 1. Check if API is running
echo "1. Checking if API is running..."
if ! curl -sf http://localhost:8000/health > /dev/null; then
    echo -e "${RED}✗ API not running${NC}"
    echo "Start with: make start"
    exit 1
fi
echo -e "${GREEN}✓ API running${NC}"
echo

# 2. Start nautilus service
echo "2. Starting Nautilus service..."
$DOCKER_COMPOSE -p $PROJECT_NAME --profile backtest up -d
sleep 5
echo

# 3. Submit test backtest
echo "3. Submitting test backtest job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:8000/jobs/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "mean_reversion_nw",
    "instrument": "ES.FUT",
    "start_date": "2024-01-01",
    "end_date": "2024-01-02",
    "config": {
      "nw_bandwidth": 20,
      "nw_std": 2.0,
      "sr_lookback": 100,
      "sr_clusters": 5
    }
  }')

if command -v jq &> /dev/null; then
    JOB_ID=$(echo $JOB_RESPONSE | jq -r '.job_id')
else
    JOB_ID=$(echo $JOB_RESPONSE | grep -oP '"job_id":"\K[^"]+')
fi

if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
    echo -e "${RED}✗ Failed to create backtest job${NC}"
    echo $JOB_RESPONSE
    exit 1
fi

echo -e "${GREEN}✓ Backtest job created: $JOB_ID${NC}"
echo

# 4. Monitor progress
echo "4. Monitoring backtest progress..."
for i in {1..30}; do
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

    echo -ne "\r  Status: $STATUS | Progress: $PROGRESS% | $MESSAGE                    "

    if [ "$STATUS" == "completed" ]; then
        echo
        echo -e "${GREEN}✓ Backtest completed successfully!${NC}"
        break
    elif [ "$STATUS" == "failed" ]; then
        echo
        echo -e "${RED}✗ Backtest failed${NC}"
        exit 1
    fi

    sleep 2
done

echo
echo

# 5. Check results
echo "5. Checking results..."
if [ -f "data/results/${JOB_ID}.json" ]; then
    echo -e "${GREEN}✓ Results file created${NC}"
    echo
    echo "Results summary:"
    if command -v jq &> /dev/null; then
        cat "data/results/${JOB_ID}.json" | jq '{strategy, instrument, total_trades, win_rate, total_pnl, sharpe_ratio}'
    else
        cat "data/results/${JOB_ID}.json"
    fi
else
    echo -e "${YELLOW}⚠ Results file not found yet${NC}"
fi

echo
echo "View logs: make logs service=nautilus_backtest"
echo "View all backtests: ls -lh data/results/"