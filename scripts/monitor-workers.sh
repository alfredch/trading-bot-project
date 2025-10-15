#!/bin/bash
# scripts/monitor-workers.sh

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

while true; do
    clear
    echo -e "${GREEN}=== Worker Monitoring Dashboard ===${NC}"
    echo

    # Worker Container Status
    echo -e "${YELLOW}Worker Containers:${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME ps worker
    echo

    # Worker Heartbeats
    echo -e "${YELLOW}Worker Heartbeats:${NC}"
    docker exec ${PROJECT_NAME}_redis redis-cli --raw KEYS "worker:*:heartbeat" 2>/dev/null | while read key; do
        if [ -n "$key" ]; then
            heartbeat=$(docker exec ${PROJECT_NAME}_redis redis-cli GET "$key" 2>/dev/null)
            echo "  $key: $heartbeat"
        fi
    done
    echo

    # Queue Status
    echo -e "${YELLOW}Queue Status:${NC}"
    migration_queue=$(docker exec ${PROJECT_NAME}_redis redis-cli LLEN queue:migration 2>/dev/null)
    backtest_queue=$(docker exec ${PROJECT_NAME}_redis redis-cli LLEN queue:backtest 2>/dev/null)
    dlq=$(docker exec ${PROJECT_NAME}_redis redis-cli LLEN queue:dlq 2>/dev/null)

    echo "  Migration Queue: $migration_queue"
    echo "  Backtest Queue: $backtest_queue"
    echo -e "  Dead Letter Queue: ${RED}$dlq${NC}"
    echo

    # Worker Metrics
    echo -e "${YELLOW}Worker Metrics:${NC}"
    docker exec ${PROJECT_NAME}_redis redis-cli --raw KEYS "worker:*:metrics" 2>/dev/null | while read key; do
        if [ -n "$key" ]; then
            echo "  $key:"
            docker exec ${PROJECT_NAME}_redis redis-cli HGETALL "$key" 2>/dev/null | \
                paste - - | sed 's/^/    /'
        fi
    done

    echo
    echo "Press Ctrl+C to exit"
    sleep 5
done