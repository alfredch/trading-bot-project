#!/bin/bash
# scripts/fix-permissions.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=== Fixing Permissions ==="
echo

# Make all scripts executable
echo -e "${YELLOW}Setting script permissions...${NC}"
find scripts -type f -name "*.sh" -exec chmod +x {} \;
chmod +x Makefile
echo -e "${GREEN}✓ Scripts are now executable${NC}"

# Fix data directory permissions
echo -e "${YELLOW}Setting data directory permissions...${NC}"
chmod -R 755 data 2>/dev/null || true
chmod -R 777 data/logs 2>/dev/null || true
chmod -R 777 data/parquet 2>/dev/null || true
chmod -R 777 data/results 2>/dev/null || true
echo -e "${GREEN}✓ Data directories permissions set${NC}"

# Fix config permissions
echo -e "${YELLOW}Setting config permissions...${NC}"
chmod -R 644 config/**/*.conf 2>/dev/null || true
chmod -R 644 config/**/*.sql 2>/dev/null || true
echo -e "${GREEN}✓ Config permissions set${NC}"

# Fix docker-compose file permissions
echo -e "${YELLOW}Setting compose file permissions...${NC}"
chmod 644 docker-compose*.yml
chmod 644 .env.example
[ -f .env ] && chmod 600 .env
echo -e "${GREEN}✓ Compose file permissions set${NC}"

echo
echo -e "${GREEN}✓ All permissions fixed${NC}"