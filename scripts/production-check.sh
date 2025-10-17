#!/bin/bash

# Production Readiness Check Script
# Verifies all production requirements are met

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0
WARNINGS=0

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((PASSED++))
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
    ((FAILED++))
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

echo "========================================="
echo "Production Readiness Check"
echo "========================================="
echo ""

# 1. Environment Configuration
echo -e "${BLUE}[1/10]${NC} Checking Environment Configuration..."

if [ -f ".env" ]; then
    check_pass "Environment file exists"

    # Check critical variables
    for var in POSTGRES_PASSWORD REDIS_HOST LOG_LEVEL; do
        if grep -q "^${var}=" .env; then
            check_pass "$var is set"
        else
            check_fail "$var is not set in .env"
        fi
    done

    # Check production settings
    if grep -q "LOG_FORMAT=json" .env; then
        check_pass "JSON logging enabled"
    else
        check_warn "JSON logging not enabled (add LOG_FORMAT=json)"
    fi

    if grep -q "DEBUG=false" .env || ! grep -q "DEBUG=" .env; then
        check_pass "Debug mode disabled"
    else
        check_warn "Debug mode is enabled (set DEBUG=false)"
    fi
else
    check_fail "Environment file (.env) not found"
fi

echo ""

# 2. Docker & Services
echo -e "${BLUE}[2/10]${NC} Checking Docker Services..."

if docker ps > /dev/null 2>&1; then
    check_pass "Docker is running"

    # Check core services
    for service in postgres redis api; do
        if docker ps | grep -q "trading_bot_${service}"; then
            check_pass "${service} container is running"
        else
            check_fail "${service} container is not running"
        fi
    done
else
    check_fail "Docker is not running or accessible"
fi

echo ""

# 3. Monitoring Stack
echo -e "${BLUE}[3/10]${NC} Checking Monitoring Stack..."

if docker ps | grep -q "trading_bot_prometheus"; then
    check_pass "Prometheus is running"
else
    check_warn "Prometheus not running (start with: make monitoring-start)"
fi

if docker ps | grep -q "trading_bot_grafana"; then
    check_pass "Grafana is running"
else
    check_warn "Grafana not running (start with: make monitoring-start)"
fi

if [ -f "config/prometheus/prometheus.yml" ]; then
    check_pass "Prometheus configuration exists"
else
    check_fail "Prometheus configuration missing"
fi

if [ -f "config/prometheus/alerts.yml" ]; then
    check_pass "Alert rules configured"
else
    check_warn "Alert rules not configured"
fi

echo ""

# 4. Health Checks
echo -e "${BLUE}[4/10]${NC} Checking Service Health..."

if curl -sf http://localhost:8010/health > /dev/null 2>&1; then
    check_pass "API health endpoint responding"

    # Check detailed health
    HEALTH=$(curl -s http://localhost:8010/health)
    if echo "$HEALTH" | grep -q '"status":"healthy"'; then
        check_pass "API reports healthy status"
    else
        check_warn "API reports degraded status"
    fi
else
    check_fail "API health endpoint not responding"
fi

echo ""

# 5. Database
echo -e "${BLUE}[5/10]${NC} Checking Database..."

if docker exec trading_bot_postgres pg_isready -U ${POSTGRES_USER:-trading_bot} > /dev/null 2>&1; then
    check_pass "PostgreSQL is accepting connections"

    # Check database size
    DB_SIZE=$(docker exec trading_bot_postgres psql -U ${POSTGRES_USER:-trading_bot} -d ${POSTGRES_DB:-trading_bot} -tAc "SELECT pg_size_pretty(pg_database_size(current_database()));" 2>/dev/null)
    if [ -n "$DB_SIZE" ]; then
        check_pass "Database size: $DB_SIZE"
    fi
else
    check_fail "PostgreSQL not accepting connections"
fi

echo ""

# 6. Redis
echo -e "${BLUE}[6/10]${NC} Checking Redis..."

if docker exec trading_bot_redis redis-cli ping > /dev/null 2>&1; then
    check_pass "Redis is responding"

    # Check memory usage
    REDIS_MEM=$(docker exec trading_bot_redis redis-cli INFO memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
    if [ -n "$REDIS_MEM" ]; then
        check_pass "Redis memory usage: $REDIS_MEM"
    fi

    # Check queue lengths
    MIGRATION_QUEUE=$(docker exec trading_bot_redis redis-cli LLEN queue:migration)
    BACKTEST_QUEUE=$(docker exec trading_bot_redis redis-cli LLEN queue:backtest)
    DLQ=$(docker exec trading_bot_redis redis-cli LLEN queue:dlq)

    echo "  Queues: Migration=$MIGRATION_QUEUE, Backtest=$BACKTEST_QUEUE, DLQ=$DLQ"

    if [ "$DLQ" -gt 10 ]; then
        check_warn "Dead letter queue has $DLQ failed jobs"
    fi
else
    check_fail "Redis not responding"
fi

echo ""

# 7. Workers
echo -e "${BLUE}[7/10]${NC} Checking Workers..."

WORKER_COUNT=$(docker ps | grep -c "worker" || echo 0)
if [ "$WORKER_COUNT" -gt 0 ]; then
    check_pass "$WORKER_COUNT worker(s) running"

    # Check worker heartbeats
    ACTIVE_WORKERS=$(docker exec trading_bot_redis redis-cli KEYS "worker:*:heartbeat" | wc -l)
    if [ "$ACTIVE_WORKERS" -gt 0 ]; then
        check_pass "$ACTIVE_WORKERS worker(s) with active heartbeat"
    else
        check_warn "No worker heartbeats detected"
    fi
else
    check_warn "No workers running (start with: make start-workers)"
fi

echo ""

# 8. Logging
echo -e "${BLUE}[8/10]${NC} Checking Logging Configuration..."

if [ -d "data/logs" ]; then
    check_pass "Log directory exists"

    # Check log files
    LOG_FILES=$(find data/logs -name "*.log" 2>/dev/null | wc -l)
    if [ "$LOG_FILES" -gt 0 ]; then
        check_pass "$LOG_FILES log file(s) found"
    fi

    # Check log rotation
    LARGE_LOGS=$(find data/logs -name "*.log" -size +100M 2>/dev/null | wc -l)
    if [ "$LARGE_LOGS" -gt 0 ]; then
        check_warn "$LARGE_LOGS log file(s) larger than 100MB (consider log rotation)"
    fi
else
    check_warn "Log directory not found"
fi

echo ""

# 9. Backups
echo -e "${BLUE}[9/10]${NC} Checking Backup Configuration..."

if [ -d "data/backups" ]; then
    check_pass "Backup directory exists"

    BACKUP_COUNT=$(ls -1 data/backups 2>/dev/null | wc -l)
    if [ "$BACKUP_COUNT" -gt 0 ]; then
        check_pass "$BACKUP_COUNT backup(s) found"

        # Check latest backup age
        LATEST_BACKUP=$(ls -t data/backups 2>/dev/null | head -1)
        if [ -n "$LATEST_BACKUP" ]; then
            BACKUP_AGE=$(( ($(date +%s) - $(stat -c %Y "data/backups/$LATEST_BACKUP" 2>/dev/null || echo 0)) / 86400 ))
            if [ "$BACKUP_AGE" -lt 7 ]; then
                check_pass "Latest backup is $BACKUP_AGE day(s) old"
            else
                check_warn "Latest backup is $BACKUP_AGE day(s) old (consider running: make backup)"
            fi
        fi
    else
        check_warn "No backups found (run: make backup)"
    fi
else
    check_warn "Backup directory not found (run: make backup)"
fi

echo ""

# 10. Resource Usage
echo -e "${BLUE}[10/10]${NC} Checking Resource Usage..."

# Check disk space
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -lt 80 ]; then
    check_pass "Disk usage: ${DISK_USAGE}%"
else
    check_warn "Disk usage high: ${DISK_USAGE}%"
fi

# Check if metrics are available
if curl -sf http://localhost:9090/api/v1/query?query=up > /dev/null 2>&1; then
    check_pass "Prometheus metrics available"
else
    check_warn "Prometheus metrics not available"
fi

echo ""
echo "========================================="
echo "Summary"
echo "========================================="
echo -e "${GREEN}Passed:${NC}   $PASSED"
echo -e "${YELLOW}Warnings:${NC} $WARNINGS"
echo -e "${RED}Failed:${NC}   $FAILED"
echo ""

if [ "$FAILED" -eq 0 ]; then
    if [ "$WARNINGS" -eq 0 ]; then
        echo -e "${GREEN}✓ System is production-ready!${NC}"
        exit 0
    else
        echo -e "${YELLOW}⚠ System has some warnings. Review recommendations above.${NC}"
        exit 0
    fi
else
    echo -e "${RED}✗ System is NOT production-ready. Fix failed checks above.${NC}"
    exit 1
fi