#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
COMPOSE_FILE="docker-compose.yml"
DOCKER_COMPOSE="docker compose"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 {start|stop|restart|logs|ps|clean|shell|migrate|backtest|status}"
    echo
    echo "Commands:"
    echo "  start [service]   - Start services (default: core services)"
    echo "  stop              - Stop all services"
    echo "  restart [service] - Restart service(s)"
    echo "  logs [service]    - Show logs"
    echo "  ps                - Show running containers"
    echo "  status            - Show detailed status of all services"
    echo "  clean             - Remove all containers and volumes"
    echo "  shell <service>   - Open shell in service"
    echo "  migrate           - Run data migration"
    echo "  backtest          - Run backtest"
    exit 1
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        echo -e "${RED}Error: Docker Compose plugin is not available${NC}"
        exit 1
    fi
}

start_services() {
    local service=$1

    if [ -z "$service" ]; then
        echo -e "${GREEN}Starting core services...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME up -d postgres redis api
    else
        echo -e "${GREEN}Starting $service...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME up -d $service
    fi

    echo -e "${GREEN}✓ Services started${NC}"
    echo
    show_ps
}

stop_services() {
    echo -e "${YELLOW}Stopping services...${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME stop
    echo -e "${GREEN}✓ Services stopped${NC}"
}

restart_services() {
    local service=$1

    if [ -z "$service" ]; then
        echo -e "${YELLOW}Restarting all services...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME restart
    else
        echo -e "${YELLOW}Restarting $service...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME restart $service
    fi

    echo -e "${GREEN}✓ Services restarted${NC}"
}

show_logs() {
    local service=$1

    if [ -z "$service" ]; then
        $DOCKER_COMPOSE -p $PROJECT_NAME logs -f --tail=100
    else
        $DOCKER_COMPOSE -p $PROJECT_NAME logs -f --tail=100 $service
    fi
}

show_ps() {
    echo -e "${GREEN}Running containers:${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME ps
}

show_status() {
    echo -e "${BLUE}=== Trading Bot System Status ===${NC}"
    echo

    # Show container status
    echo -e "${GREEN}Container Status:${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME ps
    echo

    # Show network
    echo -e "${GREEN}Network:${NC}"
    docker network inspect ${PROJECT_NAME}_network --format '{{.Name}}: {{.Driver}} ({{.IPAM.Config}})' 2>/dev/null || echo "Network not found"
    echo

    # Show volumes
    echo -e "${GREEN}Volumes:${NC}"
    docker volume ls --filter name=${PROJECT_NAME}
    echo

    # Health checks
    echo -e "${GREEN}Health Checks:${NC}"

    # Check API
    if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "  API: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  API: ${RED}✗ Unhealthy${NC}"
    fi

    # Check Redis
    if docker exec ${PROJECT_NAME}_redis redis-cli ping > /dev/null 2>&1; then
        echo -e "  Redis: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  Redis: ${RED}✗ Unhealthy${NC}"
    fi

    # Check PostgreSQL
    if docker exec ${PROJECT_NAME}_postgres pg_isready -U trading_user > /dev/null 2>&1; then
        echo -e "  PostgreSQL: ${GREEN}✓ Healthy${NC}"
    else
        echo -e "  PostgreSQL: ${RED}✗ Unhealthy${NC}"
    fi
    echo
}

clean_project() {
    echo -e "${RED}⚠️  This will remove all containers, networks, and volumes!${NC}"
    read -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" == "yes" ]; then
        echo -e "${YELLOW}Cleaning project...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME down -v
        echo -e "${GREEN}✓ Project cleaned${NC}"
    else
        echo "Cancelled"
    fi
}

open_shell() {
    local service=$1

    if [ -z "$service" ]; then
        echo -e "${RED}Please specify a service${NC}"
        echo "Available services:"
        $DOCKER_COMPOSE -p $PROJECT_NAME ps --services
        exit 1
    fi

    echo -e "${GREEN}Opening shell in $service...${NC}"
    $DOCKER_COMPOSE -p $PROJECT_NAME exec $service /bin/bash
}

run_migration() {
    echo -e "${GREEN}Starting data migration...${NC}"
    echo

    # Check if API is running
    if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${YELLOW}API is not running. Starting core services...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME up -d postgres redis api
        echo "Waiting for services to be ready..."
        sleep 10
    fi

    # Start data pipeline worker
    echo "Starting data pipeline worker..."
    $DOCKER_COMPOSE -p $PROJECT_NAME --profile pipeline up -d data_pipeline

    echo
    echo -e "${GREEN}Data pipeline started.${NC}"
    echo "Submit migration jobs via API:"
    echo "  curl -X POST http://localhost:8000/jobs/migrate \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"instrument\": \"ES.FUT\", \"start_date\": \"2024-01-01\", \"end_date\": \"2024-12-31\"}'"
    echo
    echo "Monitor logs: make logs service=data_pipeline"
}

run_backtest() {
    echo -e "${GREEN}Starting backtest service...${NC}"
    echo

    # Check if API is running
    if ! curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
        echo -e "${YELLOW}API is not running. Starting core services...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME up -d postgres redis api
        echo "Waiting for services to be ready..."
        sleep 10
    fi

    # Start backtest and workers
    echo "Starting backtest services..."
    $DOCKER_COMPOSE -p $PROJECT_NAME --profile backtest --profile workers up -d

    echo
    echo -e "${GREEN}Backtest services started.${NC}"
    echo "Submit backtest jobs via API:"
    echo "  curl -X POST http://localhost:8000/jobs/backtest \\"
    echo "    -H 'Content-Type: application/json' \\"
    echo "    -d '{\"strategy_name\": \"mean_reversion_nw\", \"instrument\": \"ES.FUT\", ...}'"
    echo
    echo "Monitor logs: make logs service=worker"
}

# Check Docker availability
check_docker

# Main script
case "$1" in
    start)
        start_services "$2"
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services "$2"
        ;;
    logs)
        show_logs "$2"
        ;;
    ps)
        show_ps
        ;;
    status)
        show_status
        ;;
    clean)
        clean_project
        ;;
    shell)
        open_shell "$2"
        ;;
    migrate)
        run_migration
        ;;
    backtest)
        run_backtest
        ;;
    *)
        usage
        ;;
esac