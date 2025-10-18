#!/bin/bash
# Migrate from deprecated 'docker-compose' to 'docker compose' v2
# This script updates all documentation and scripts

set -e

echo "=================================================="
echo "🔄 Migrating docker-compose to docker compose v2"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Counter
updated_files=0

# Function to update file
update_file() {
    local file=$1

    if [ ! -f "$file" ]; then
        echo -e "${YELLOW}⚠️  Skipping $file (not found)${NC}"
        return
    fi

    # Check if file contains docker-compose
    if ! grep -q "docker-compose" "$file"; then
        echo "   ✓ $file (no changes needed)"
        return
    fi

    # Create backup
    cp "$file" "$file.bak"

    # Replace docker-compose with docker compose
    # But preserve docker-compose.yml filenames
    sed -i.tmp \
        -e 's/docker-compose \(up\|down\|build\|restart\|logs\|ps\|exec\|run\|stop\|start\|kill\|rm\|pull\|push\|config\|scale\|top\|pause\|unpause\)/docker compose \1/g' \
        "$file"

    # Also handle cases with -f flag
    sed -i.tmp \
        -e 's/docker-compose -f \([^ ]*\)/docker compose -f \1/g' \
        "$file"

    # Remove temp file
    rm -f "$file.tmp"

    echo -e "${GREEN}   ✅ Updated $file${NC}"
    ((updated_files++))
}

echo "Updating documentation files..."
echo "-----------------------------------"

# Update