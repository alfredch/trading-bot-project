# Quick Reference Guide

## Docker Compose Commands

All commands use `docker compose` (not `docker-compose`):
```bash
# Start services
docker compose -p trading_bot up -d

# Stop services
docker compose -p trading_bot stop

# View logs
docker compose -p trading_bot logs -f

# List containers
docker compose -p trading_bot ps

# Execute command in container
docker compose -p trading_bot exec api /bin/bash

# Restart service
docker compose -p trading_bot restart api

# Remove everything
docker compose -p trading_bot down -v

# Build images
docker compose -p trading_bot build

# Pull images
docker compose -p trading_bot pull

# Scale workers
docker compose -p trading_bot up -d --scale worker=4

--------------- Docker Compose Commands --------------- 
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

--------------------- Monitoring -------------------
# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access dashboards
# Grafana: http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090