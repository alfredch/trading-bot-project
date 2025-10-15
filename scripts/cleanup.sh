#!/bin/bash

set -e

PROJECT_NAME="trading_bot"
DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Trading Bot Cleanup ===${NC}"
echo

# Menu
echo "What would you like to clean?"
echo "1) Stop containers (keep data)"
echo "2) Remove containers and networks (keep volumes)"
echo "3) Remove everything including volumes (⚠ DATA LOSS)"
echo "4) Clean Docker system (unused images, containers, networks)"
echo "5) Clean logs only"
echo "6) Cancel"
echo

read -p "Enter choice [1-6]: " choice

case $choice in
    1)
        echo -e "${YELLOW}Stopping containers...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME stop
        echo -e "${GREEN}✓ Containers stopped${NC}"
        ;;
    2)
        echo -e "${YELLOW}Removing containers and networks...${NC}"
        $DOCKER_COMPOSE -p $PROJECT_NAME down
        echo -e "${GREEN}✓ Cleanup complete. Volumes preserved.${NC}"
        ;;
    3)
        echo -e "${RED}⚠ WARNING: This will delete ALL data!${NC}"
        read -p "Type 'DELETE' to confirm: " confirm
        if [ "$confirm" == "DELETE" ]; then
            echo -e "${YELLOW}Removing everything...${NC}"
            $DOCKER_COMPOSE -p $PROJECT_NAME down -v --rmi local
            echo -e "${GREEN}✓ Complete cleanup done${NC}"
        else
            echo "Cancelled"
        fi
        ;;
    4)
        echo -e "${YELLOW}Cleaning Docker system...${NC}"
        docker system prune -af --volumes
        echo -e "${GREEN}✓ Docker system cleaned${NC}"
        ;;
    5)
        echo -e "${YELLOW}Cleaning logs...${NC}"
        find ./data/logs -name "*.log" -type f -delete
        echo -e "${GREEN}✓ Logs cleaned${NC}"
        ;;
    6)
        echo "Cancelled"
        exit 0
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

# Show disk space saved
echo
echo -e "${GREEN}Disk space status:${NC}"
df -h . | awk 'NR==1 || NR==2'