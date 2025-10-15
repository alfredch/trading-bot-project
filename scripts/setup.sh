#!/bin/bash
# scripts/setup.sh - Complete setup script

set -e

DOCKER_COMPOSE="docker compose"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
cat << "EOF"
╔════════════════════════════════════════╗
║   Trading Bot - Complete Setup         ║
╚════════════════════════════════════════╝
EOF
echo -e "${NC}"

# Step 1: Check Docker
echo -e "${YELLOW}Step 1/7: Checking Docker environment...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Install: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo -e "${RED}✗ Docker Compose plugin not installed${NC}"
    echo "Install: sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo -e "${GREEN}✓ Docker version: $(docker --version)${NC}"
echo -e "${GREEN}✓ Docker Compose: $(docker compose version --short)${NC}"
echo

# Step 2: Check user permissions
echo -e "${YELLOW}Step 2/7: Checking user permissions...${NC}"
if docker ps &> /dev/null; then
    echo -e "${GREEN}✓ User has Docker permissions${NC}"
else
    echo -e "${RED}✗ User needs Docker permissions${NC}"
    echo "Run: sudo usermod -aG docker $USER"
    echo "Then logout and login again"
    exit 1
fi
echo

# Step 3: Generate .env if not exists
echo -e "${YELLOW}Step 3/7: Setting up environment configuration...${NC}"
if [ ! -f .env ]; then
    read -p "Generate .env with secure passwords? (yes/no): " gen_env
    if [ "$gen_env" == "yes" ]; then
        bash scripts/generate-env.sh
    else
        echo "Copying from .env.example..."
        cp .env.example .env
        echo -e "${YELLOW}⚠ Please edit .env and set secure passwords${NC}"
    fi
else
    echo -e "${GREEN}✓ .env file exists${NC}"
fi
echo

# Step 4: Create directory structure
echo -e "${YELLOW}Step 4/7: Creating directory structure...${NC}"
mkdir -p data/{parquet,results,logs}
mkdir -p data/parquet/{ES.FUT,6E.FUT}
mkdir -p data/results/{ES.FUT,6E.FUT}
mkdir -p data/logs/{postgres,redis,api,worker,data_pipeline,nautilus}
mkdir -p data/volumes/{postgres,redis}

# Create .gitkeep files
find data -type d -exec touch {}/.gitkeep \; 2>/dev/null

echo -e "${GREEN}✓ Directory structure created${NC}"
echo

# Step 5: Fix permissions
echo -e "${YELLOW}Step 5/7: Setting permissions...${NC}"
bash scripts/fix-permissions.sh
echo

# Step 6: Initialize volumes
echo -e "${YELLOW}Step 6/7: Initializing Docker volumes...${NC}"
if command -v sudo &> /dev/null; then
    bash scripts/init-volumes.sh
else
    echo -e "${YELLOW}⚠ Skipping volume initialization (sudo not available)${NC}"
fi
echo

# Step 7: Build Docker images
echo -e "${YELLOW}Step 7/7: Building Docker images...${NC}"
echo "This may take several minutes..."
if $DOCKER_COMPOSE -p trading_bot build --progress=plain; then
    echo -e "${GREEN}✓ Docker images built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build Docker images${NC}"
    exit 1
fi
echo

# Summary
echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Setup Complete!               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo
echo -e "${GREEN}Next steps:${NC}"
echo "  1. Review .env configuration: nano .env"
echo "  2. Start services: make start"
echo "  3. Check status: make status"
echo "  4. View all commands: make help"
echo
echo -e "${YELLOW}Useful commands:${NC}"
echo "  make start         # Start core services"
echo "  make status        # Check system health"
echo "  make logs          # View logs"
echo "  make help          # Show all commands"
echo
echo "Documentation: ./docs/"
echo "Support: Check README.md for more information"