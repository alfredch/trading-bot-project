#!/bin/bash

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== Trading Bot Health Check ===${NC}"
echo

# Function to check service health
check_service() {
    local service=$1
    local check_command=$2

    if eval "$check_command" &>/dev/null; then
        echo -e "  $service: ${GREEN}✓ Healthy${NC}"
        return 0
    else
        echo -e "  $service: ${RED}✗ Unhealthy${NC}"
        return 1
    fi
}

# Check if containers are running
echo -e "${YELLOW}Checking container status...${NC}"
CONTAINERS_UP=$($DOCKER_COMPOSE -p $PROJECT_NAME ps --services --filter "status=running" | wc -l)
CONTAINERS_TOTAL=$($DOCKER_COMPOSE -p $PROJECT_NAME ps --services | wc -l)
echo "  Containers running: $CONTAINERS_UP/$CONTAINERS_TOTAL"
echo

# Check individual services
echo -e "${YELLOW}Checking service health...${NC}"

check_service "PostgreSQL" \
    "docker exec ${PROJECT_NAME}_postgres pg_isready -U trading_user"

check_service "Redis" \
    "docker exec ${PROJECT_NAME}_redis redis-cli ping"

check_service "API" \
    "curl -sf http://localhost:8000/health"

echo

# Check network
echo -e "${YELLOW}Checking network...${NC}"
if docker network inspect ${PROJECT_NAME}_network &>/dev/null; then
    echo -e "  Network: ${GREEN}✓ Active${NC}"
    NETWORK_CONTAINERS=$(docker network inspect ${PROJECT_NAME}_network -f '{{len .Containers}}')
    echo "  Connected containers: $NETWORK_CONTAINERS"
else
    echo -e "  Network: ${RED}✗ Not found${NC}"
fi
echo

# Check volumes
echo -e "${YELLOW}Checking volumes...${NC}"
POSTGRES_VOL=$(docker volume ls -qf name=${PROJECT_NAME}_postgres_data)
REDIS_VOL=$(docker volume ls -qf name=${PROJECT_NAME}_redis_data)

if [ -n "$POSTGRES_VOL" ]; then
    echo -e "  PostgreSQL volume: ${GREEN}✓ Exists${NC}"
    POSTGRES_SIZE=$(docker system df -v | grep "$POSTGRES_VOL" | awk '{print $3}')
    echo "    Size: $POSTGRES_SIZE"
else
    echo -e "  PostgreSQL volume: ${RED}✗ Not found${NC}"
fi

if [ -n "$REDIS_VOL" ]; then
    echo -e "  Redis volume: ${GREEN}✓ Exists${NC}"
    REDIS_SIZE=$(docker system df -v | grep "$REDIS_VOL" | awk '{print $3}')
    echo "    Size: $REDIS_SIZE"
else
    echo -e "  Redis volume: ${RED}✗ Not found${NC}"
fi
echo

# Check disk space
echo -e "${YELLOW}Checking disk space...${NC}"
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
DISK_AVAIL=$(df -h . | awk 'NR==2 {print $4}')

if [ "$DISK_USAGE" -lt 80 ]; then
    echo -e "  Disk usage: ${GREEN}$DISK_USAGE% (${DISK_AVAIL} available)${NC}"
elif [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "  Disk usage: ${YELLOW}$DISK_USAGE% (${DISK_AVAIL} available)${NC}"
else
    echo -e "  Disk usage: ${RED}$DISK_USAGE% (${DISK_AVAIL} available)${NC}"
fi
echo

# Check memory
echo -e "${YELLOW}Checking memory usage...${NC}"
TOTAL_MEM=$(free -h | awk 'NR==2 {print $2}')
USED_MEM=$(free -h | awk 'NR==2 {print $3}')
AVAIL_MEM=$(free -h | awk 'NR==2 {print $7}')
echo "  Total: $TOTAL_MEM | Used: $USED_MEM | Available: $AVAIL_MEM"
echo

# Check CPU
echo -e "${YELLOW}Checking CPU usage...${NC}"
CPU_USAGE=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | cut -d'%' -f1)
echo "  CPU usage: ${CPU_USAGE}%"
echo

# Check logs for errors
echo -e "${YELLOW}Checking recent errors in logs...${NC}"
ERROR_COUNT=$(find ./data/logs -name "*.log" -type f -mtime -1 -exec grep -i "error\|exception\|failed" {} \; 2>/dev/null | wc -l)
if [ "$ERROR_COUNT" -eq 0 ]; then
    echo -e "  Recent errors: ${GREEN}0 found${NC}"
elif [ "$ERROR_COUNT" -lt 10 ]; then
    echo -e "  Recent errors: ${YELLOW}$ERROR_COUNT found${NC}"
else
    echo -e "  Recent errors: ${RED}$ERROR_COUNT found${NC}"
fi
echo

# Summary
echo -e "${BLUE}=== Summary ===${NC}"
if [ "$CONTAINERS_UP" -eq "$CONTAINERS_TOTAL" ] && \
   [ -n "$POSTGRES_VOL" ] && \
   [ -n "$REDIS_VOL" ] && \
   [ "$DISK_USAGE" -lt 90 ]; then
    echo -e "${GREEN}✓ System is healthy${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠ Some issues detected${NC}"
    exit 1
fi