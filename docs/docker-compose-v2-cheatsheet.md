# 🚀 Docker Compose v2 - Quick Reference

## Essential Commands

### Service Management
```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d nautilus_backtest

# Stop all services
docker compose down

# Stop specific service
docker compose stop nautilus_backtest

# Restart service
docker compose restart nautilus_backtest

# Remove stopped containers
docker compose rm
```

### Building
```bash
# Build all services
docker compose build

# Build specific service
docker compose build nautilus_backtest

# Build without cache
docker compose build --no-cache

# Pull images
docker compose pull
```

### Logs & Monitoring
```bash
# View logs (all services)
docker compose logs

# Follow logs
docker compose logs -f

# Logs for specific service
docker compose logs -f nautilus_backtest

# Last 100 lines
docker compose logs --tail=100 nautilus_backtest

# Real-time stats
docker stats
```

### Executing Commands
```bash
# Execute command in running container
docker compose exec nautilus_backtest bash

# Run one-off command
docker compose run nautilus_backtest python3 --version

# Execute as specific user
docker compose exec -u root nautilus_backtest apt-get update
```

### Status & Info
```bash
# List running services
docker compose ps

# Show service configuration
docker compose config

# Validate compose file
docker compose config --quiet

# Show service ports
docker compose port nautilus_backtest 8000
```

### Scaling
```bash
# Scale service to 3 instances
docker compose up -d --scale nautilus_backtest=3

# Scale multiple services
docker compose up -d --scale worker=5 --scale api=2
```

---

## Common Workflows

### Development Workflow
```bash
# 1. Start services
docker compose up -d

# 2. Watch logs
docker compose logs -f

# 3. Make changes to code

# 4. Rebuild
docker compose build nautilus_backtest

# 5. Restart
docker compose restart nautilus_backtest

# 6. Test
docker compose exec nautilus_backtest ./test.sh
```

### Debugging Workflow
```bash
# Enter container
docker compose exec nautilus_backtest bash

# Check logs
docker compose logs nautilus_backtest | grep ERROR

# Inspect config
docker compose config

# Check processes
docker compose top

# View resource usage
docker stats nautilus_backtest
```

### Production Deployment
```bash
# Pull latest images
docker compose pull

# Rebuild services
docker compose build

# Stop old containers
docker compose down

# Start with new images
docker compose up -d

# Verify health
docker compose ps
curl http://localhost:8000/health
```

---

## File Operations

### Using Different Compose Files
```bash
# Use specific file
docker compose -f compose.prod.yml up -d

# Use multiple files (merge)
docker compose -f docker-compose.yml -f compose.override.yml up -d

# Environment-specific
docker compose -f compose.staging.yml up -d
```

### Project Names
```bash
# Use custom project name
docker compose -p myproject up -d

# List projects
docker compose ls

# Remove project
docker compose -p myproject down
```

---

## Advanced Commands

### Networks
```bash
# List networks
docker network ls

# Inspect network
docker network inspect trading-bot-project_default

# Connect service to network
docker compose exec nautilus_backtest ping redis
```

### Volumes
```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect trading-bot-project_postgres

# Remove unused volumes
docker volume prune
```

### Cleanup
```bash
# Remove stopped containers
docker compose rm

# Remove everything
docker compose down -v --remove-orphans

# Remove images too
docker compose down --rmi all

# System-wide cleanup
docker system prune -a
```

---

## Environment Variables

### Using .env File
```bash
# .env file in project root
POSTGRES_PASSWORD=secret
REDIS_PORT=6379

# Access in compose.yml
services:
  db:
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
```

### Override from Command Line
```bash
# Set variable for this command
REDIS_PORT=6380 docker compose up -d

# Or export first
export REDIS_PORT=6380
docker compose up -d
```

---

## Nautilus Backtest Specific

### Start Backtest Service
```bash
# Start service
docker compose up -d nautilus_backtest

# Check status
docker compose ps nautilus_backtest

# View logs
docker compose logs -f nautilus_backtest
```

### Run Tests
```bash
# Execute test script
docker compose exec nautilus_backtest ./test-nautilus-strategy.sh

# Or enter container and run manually
docker compose exec nautilus_backtest bash
./test-nautilus-strategy.sh
```

### Debug Strategy
```bash
# Check strategy file
docker compose exec nautilus_backtest cat /app/strategies/mean_reversion_nw.py

# Test import
docker compose exec nautilus_backtest python3 -c "
import sys
sys.path.insert(0, '/app')
from strategies.mean_reversion_nw import MeanReversionNWStrategy
print('OK')
"

# Check data
docker compose exec nautilus_backtest ls -la /data/parquet/
```

### Monitor Backtests
```bash
# Watch for signals
docker compose logs -f nautilus_backtest | grep -E "(LONG|SHORT|EXIT)"

# Check Redis queue
docker compose exec redis redis-cli LLEN queue:backtest

# Monitor resources
docker stats nautilus_backtest
```

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker compose logs nautilus_backtest

# Validate config
docker compose config

# Check dependencies
docker compose up nautilus_backtest

# Force recreate
docker compose up -d --force-recreate nautilus_backtest
```

### Port Already in Use
```bash
# Find process using port
lsof -i :8000

# Or change port in compose file
ports:
  - "8001:8000"  # Use 8001 instead
```

### Permission Issues
```bash
# Run as root
docker compose exec -u root nautilus_backtest bash

# Fix permissions
docker compose exec -u root nautilus_backtest chown -R app:app /app
```

### Out of Disk Space
```bash
# Check disk usage
docker system df

# Clean up
docker system prune -a --volumes

# Remove old images
docker image prune -a
```

---

## Tips & Tricks

### Aliases
```bash
# Add to .bashrc or .zshrc
alias dc='docker compose'
alias dcu='docker compose up -d'
alias dcd='docker compose down'
alias dcl='docker compose logs -f'
alias dce='docker compose exec'
alias dcb='docker compose build'
```

### Watch Logs of Multiple Services
```bash
# Watch specific services
docker compose logs -f nautilus_backtest worker api
```

### Quick Rebuild
```bash
# Rebuild and restart in one command
docker compose up -d --build nautilus_backtest
```

### Copy Files
```bash
# From container to host
docker compose cp nautilus_backtest:/data/results/result.json ./

# From host to container
docker compose cp ./config.json nautilus_backtest:/app/config.json
```

### Database Commands
```bash
# PostgreSQL
docker compose exec postgres psql -U user -d database

# Redis
docker compose exec redis redis-cli
```

---

## Quick Checks

```bash
# ✅ Is service running?
docker compose ps nautilus_backtest

# ✅ Is it healthy?
docker compose ps | grep healthy

# ✅ What ports are exposed?
docker compose port nautilus_backtest 8000

# ✅ Can it connect to Redis?
docker compose exec nautilus_backtest redis-cli -h redis ping

# ✅ Can it access data?
docker compose exec nautilus_backtest ls /data/parquet/

# ✅ Is API reachable?
curl http://localhost:8000/health
```

---

**Remember:** `docker compose` (no hyphen!) is the new standard! 🚀