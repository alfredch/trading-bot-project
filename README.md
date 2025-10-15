## Quick Start

### Prerequisites

- Docker 24.0+ with Compose plugin
- Ubuntu 24.04 LTS (or similar)
- 16GB+ RAM recommended
- 100GB+ free disk space for data

### Verify Docker Installation
```bash
# Check Docker version
docker --version
# Should show: Docker version 24.0 or higher

# Check Docker Compose plugin
docker compose version
# Should show: Docker Compose version v2.x.x

# If Docker Compose plugin is not installed:
sudo apt-get update
sudo apt-get install docker-compose-plugin
```


## All Available Make Commands

### Setup Commands
```bash
make check          # Check Docker environment
make setup          # Complete initial setup
```
### Service Management
```bash
make start          # Start core services (postgres, redis, api)
make start-dev      # Start in development mode
make start-all      # Start all services including workers
make stop           # Stop all services
make restart        # Restart all services
make status         # Show detailed system status
make health         # Run comprehensive health check
make ps             # Show running containers
```
### Worker & Pipeline Commands
```bash
make start-workers  # Start worker services
make start-pipeline # Start data pipeline
make start-backtest # Start backtest service
make scale workers=4  # Scale workers to 4 instances
```
### Logging & Debugging
```bash
make logs           # Show all logs
make logs service=api  # Show logs for specific service
make logs-watch     # Interactive log viewer
make shell service=api  # Open shell in service
```
### Data Management
```bash
make migrate        # Run data migration wizard
make backtest       # Run backtest wizard
make backup         # Backup all data and config
make restore        # Restore data from backup
```
### Maintenance
```bash
make build          # Build all Docker images
make build-no-cache # Build without cache
make pull           # Pull latest base images
make update         # Update entire system
make clean          # Interactive cleanup menu
make clean-full     # Remove everything (⚠️ data loss)
make test           # Run all tests
```
### Direct Script execution
```bash
./scripts/setup.sh              # Run setup
./scripts/quickstart.sh         # One-command setup & start
./scripts/health-check.sh       # Comprehensive health check
./scripts/migrate_data.sh       # Migration wizard
./scripts/scale-workers.sh 4    # Scale workers
./scripts/backup.sh             # Backup data
./scripts/cleanup.sh            # Cleanup wizard
./scripts/logs-watch.sh api     # Watch logs
./scripts/fix-permissions.sh    # Fix file permissions
./scripts/generate-env.sh       # Generate secure .env
```
### Monitoring (Optional)
```bash
# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```
### Docker Compose Commands
```bash
# Basic operations
docker compose -p trading_bot up -d
docker compose -p trading_bot down
docker compose -p trading_bot ps
docker compose -p trading_bot logs -f

# Scaling
docker compose -p trading_bot up -d --scale worker=4

# Profiles
docker compose -p trading_bot --profile workers up -d
docker compose -p trading_bot --profile pipeline up -d
docker compose -p trading_bot --profile backtest up -d

# Rebuild
docker compose -p trading_bot build --no-cache
docker compose -p trading_bot up -d --build
```
### Troubleshooting
#### File permissions
```bash
./scripts/fix-permissions.sh
sudo chown -R $USER:$USER data/
```
#### Docker Compose Not Found
```bash
# Install Docker Compose plugin
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify
docker compose version
```
#### Services Won't Start
```bash
# Check logs
make logs service=postgres
make logs service=redis

# Check health
make health

# Full restart
make stop
make clean
make start
```
#### Out of Memory
```bash
# Check Docker stats
docker stats

# Adjust memory in .env
POSTGRES_SHARED_BUFFERS=1GB
REDIS_MAXMEMORY=1gb
```
#### Environment Variables for Production
```bash
# Use strong passwords
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>

# Optimize for production
LOG_LEVEL=WARNING
DEV_MODE=false
DEBUG=false

# Resource limits
POSTGRES_SHARED_BUFFERS=4GB
REDIS_MAXMEMORY=4gb
WORKER_REPLICAS=4
```
#### Backkup Strategy
```bash
# Automated daily backup
crontab -e

# Add line:
0 2 * * * cd /path/to/trading-bot-project && make backup
```