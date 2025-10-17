#!/bin/bash
echo "Cleaning up Docker resources..."

# Stop containers
docker compose -p trading_bot -f docker-compose.yml -f docker-compose.monitoring.yml down

# Kill zombie docker-proxy processes
sudo pkill -9 docker-proxy 2>/dev/null || true

# Wait
sleep 2

# Verify ports are free
echo "Checking ports..."
sudo ss -tulpn | grep -E "909[0-9]|8010|3000" || echo "All ports free ✓"

echo "Cleanup complete!"