#!/bin/bash
set -e

echo "========================================="
echo "Trading Bot - Monitoring Setup"
echo "========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running from project root
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}Error: Must run from project root${NC}"
    exit 1
fi

echo "Step 1: Creating monitoring directories..."
mkdir -p config/prometheus
mkdir -p config/alertmanager
mkdir -p config/grafana/provisioning/datasources
mkdir -p config/grafana/provisioning/dashboards
mkdir -p config/grafana/dashboards

echo -e "${GREEN}✓${NC} Directories created"
echo ""

echo "Step 2: Setting up Grafana admin password..."
read -sp "Enter Grafana admin password (default: admin): " GRAFANA_PASSWORD
echo ""
GRAFANA_PASSWORD=${GRAFANA_PASSWORD:-admin}

# Update or create .env
if grep -q "GRAFANA_ADMIN_PASSWORD" .env 2>/dev/null; then
    sed -i "s/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASSWORD}/" .env
else
    echo "GRAFANA_ADMIN_PASSWORD=${GRAFANA_PASSWORD}" >> .env
fi

echo -e "${GREEN}✓${NC} Grafana password configured"
echo ""

echo "Step 3: Copying configuration files..."
# These files should already exist from the artifacts
if [ ! -f "config/prometheus/prometheus.yml" ]; then
    echo -e "${YELLOW}Warning: config/prometheus/prometheus.yml not found${NC}"
    echo "Please create it using the provided artifact"
fi

if [ ! -f "config/prometheus/alerts.yml" ]; then
    echo -e "${YELLOW}Warning: config/prometheus/alerts.yml not found${NC}"
    echo "Please create it using the provided artifact"
fi

if [ ! -f "config/alertmanager/alertmanager.yml" ]; then
    echo -e "${YELLOW}Warning: config/alertmanager/alertmanager.yml not found${NC}"
    echo "Please create it using the provided artifact"
fi

echo -e "${GREEN}✓${NC} Configuration check complete"
echo ""

echo "Step 4: Starting monitoring stack..."
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

echo ""
echo -e "${GREEN}✓${NC} Monitoring stack started"
echo ""

echo "========================================="
echo "Monitoring URLs:"
echo "========================================="
echo -e "${GREEN}Grafana:${NC}     http://localhost:3000"
echo "             Username: admin"
echo "             Password: ${GRAFANA_PASSWORD}"
echo ""
echo -e "${GREEN}Prometheus:${NC}  http://localhost:9090"
echo -e "${GREEN}AlertManager:${NC} http://localhost:9093"
echo ""
echo "========================================="
echo "Next Steps:"
echo "========================================="
echo "1. Open Grafana at http://localhost:3000"
echo "2. Login with admin/${GRAFANA_PASSWORD}"
echo "3. Navigate to Dashboards → Trading Bot Dashboard"
echo "4. Configure AlertManager notifications (optional)"
echo ""
echo -e "${YELLOW}Note:${NC} It may take 30-60 seconds for all metrics to appear"
echo ""

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 10

# Check health
echo ""
echo "Checking service health..."

check_service() {
    local service=$1
    local url=$2

    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service is not responding"
        return 1
    fi
}

check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"
check_service "API" "http://localhost:8010/health"

echo ""
echo -e "${GREEN}Setup complete!${NC}"
echo ""