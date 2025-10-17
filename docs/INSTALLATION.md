# Production-Ready Installation Guide

Complete guide to upgrade your Trading Bot system to production-ready status with monitoring and observability.

## 📋 Prerequisites

- Existing trading-bot-project installation
- Docker 24.0+ with Compose plugin
- 16GB+ RAM (32GB recommended for production)
- 100GB+ free disk space
- Ubuntu 24.04 LTS or similar

## 🚀 Installation Steps

### Step 1: Update Project Files

The following new files need to be added to your project:

#### 1.1 Monitoring Stack Configuration

Create monitoring configuration files:

```bash
# Create monitoring directories
mkdir -p config/{prometheus,alertmanager,grafana/{provisioning/datasources,provisioning/dashboards,dashboards}}

# Copy monitoring configuration files
# (Use artifacts provided in this upgrade)
```

**Files to create:**
- `docker-compose.monitoring.yml` - Monitoring services
- `config/prometheus/prometheus.yml` - Prometheus config
- `config/prometheus/alerts.yml` - Alert rules
- `config/alertmanager/alertmanager.yml` - Alert manager config
- `config/grafana/provisioning/datasources/prometheus.yml` - Grafana datasources
- `config/grafana/provisioning/dashboards/dashboards.yml` - Dashboard provisioning
- `config/grafana/dashboards/trading-bot-dashboard.json` - Main dashboard

#### 1.2 API Service Updates

Update API service files:

```bash
# Create new directories
mkdir -p services/api/src/middleware

# Copy updated files
# (Use artifacts provided)
```

**Files to create/update:**
- `services/api/src/middleware/metrics.py` - NEW: Prometheus metrics middleware
- `services/api/src/main.py` - UPDATE: Enhanced with metrics and monitoring
- `services/api/requirements.txt` - UPDATE: Add prometheus-client and python-json-logger

#### 1.3 Worker Service Updates

Update worker service files:

```bash
# Copy updated files
mkdir -p services/worker/src
```

**Files to create/update:**
- `services/worker/src/metrics.py` - NEW: Worker metrics exporter
- `services/worker/src/worker.py` - UPDATE: Enhanced with circuit breaker and metrics
- `services/worker/requirements.txt` - UPDATE: Add prometheus-client, python-json-logger, psutil

#### 1.4 Scripts and Automation

Add production scripts:

```bash
chmod +x scripts/*.sh
```

**Files to create:**
- `scripts/setup-monitoring.sh` - NEW: Monitoring setup script
- `scripts/production-check.sh` - NEW: Production readiness check
- `Makefile.monitoring` - NEW: Monitoring-related Makefile targets

#### 1.5 Documentation

Add production documentation:

```bash
mkdir -p docs
```

**Files to create:**
- `docs/PRODUCTION.md` - Production deployment guide
- `docs/INSTALLATION.md` - This file
- `.env.production.example` - Production environment template

### Step 2: Update Dependencies

Update Python dependencies for all services:

```bash
# API Service
cd services/api
pip install prometheus-client==0.19.0 python-json-logger==2.0.7

# Worker Service
cd ../worker
pip install prometheus-client==0.19.0 python-json-logger==2.0.7 psutil==5.9.7

# Rebuild Docker images
cd ../..
docker compose -p trading_bot build --no-cache
```

### Step 3: Configure Production Environment

```bash
# Copy production environment template
cp .env.production.example .env.production

# Edit with your production values
nano .env.production

# Important values to change:
# - POSTGRES_PASSWORD (strong password)
# - REDIS_PASSWORD (strong password)
# - GRAFANA_ADMIN_PASSWORD (strong password)
# - LOG_FORMAT=json
# - LOG_LEVEL=INFO
```

### Step 4: Setup Monitoring Stack

```bash
# Run monitoring setup script
bash scripts/setup-monitoring.sh

# This will:
# 1. Create required directories
# 2. Configure Grafana password
# 3. Start monitoring services
# 4. Verify health
```

### Step 5: Update Makefile

Add monitoring targets to your Makefile:

```bash
# Option 1: Include the monitoring Makefile
echo "include Makefile.monitoring" >> Makefile

# Option 2: Copy targets manually
# (Copy targets from Makefile.monitoring into your Makefile)
```

### Step 6: Restart Services with New Configuration

```bash
# Stop all services
make stop

# Start with production configuration
docker compose -p trading_bot -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Verify all services are running
make status
```

### Step 7: Verify Installation

Run the production readiness check:

```bash
make prod-check
```

Expected output:
```
========================================
Production Readiness Check
========================================

[1/10] Checking Environment Configuration...
✓ Environment file exists
✓ POSTGRES_PASSWORD is set
✓ JSON logging enabled
...

Summary
========================================
Passed:   25
Warnings: 2
Failed:   0

✓ System is production-ready!
```

### Step 8: Access Monitoring Dashboards

Open your browser and navigate to:

1. **Grafana**: http://localhost:3000
   - Login: admin / (your configured password)
   - Navigate to: Dashboards → Trading Bot Dashboard

2. **Prometheus**: http://localhost:9090
   - Verify targets are up: Status → Targets

3. **AlertManager**: http://localhost:9093
   - Check alert configuration

### Step 9: Configure Alerts (Optional)

Edit alert configuration for your notification channels:

```bash
nano config/alertmanager/alertmanager.yml
```

Add your email, Slack, or PagerDuty configuration:

```yaml
receivers:
  - name: 'critical'
    email_configs:
      - to: 'ops@your-domain.com'
        from: 'alerts@trading-bot.local'
    slack_configs:
      - api_url: 'YOUR_SLACK_WEBHOOK_URL'
        channel: '#alerts-critical'
```

Restart AlertManager:
```bash
docker compose -p trading_bot restart alertmanager
```

## 🔧 Post-Installation Configuration

### Enable Structured Logging

Update `.env`:
```bash
LOG_FORMAT=json
LOG_LEVEL=INFO
```

Restart services:
```bash
docker compose -p trading_bot restart api worker
```

### Configure Backup Schedule

Add to crontab:
```bash
crontab -e

# Add daily backup at 2 AM
0 2 * * * cd /path/to/trading-bot-project && make backup

# Add weekly cleanup
0 3 * * 0 cd /path/to/trading-bot-project && scripts/cleanup.sh
```

### Optimize Resource Limits

Edit `.env` based on your hardware:

```bash
# For 32GB RAM system
POSTGRES_SHARED_BUFFERS=8GB
REDIS_MAXMEMORY=4gb
WORKER_REPLICAS=4
WORKER_MEMORY_LIMIT=4gb

# For 64GB RAM system
POSTGRES_SHARED_BUFFERS=16GB
REDIS_MAXMEMORY=8gb
WORKER_REPLICAS=8
WORKER_MEMORY_LIMIT=6gb
```

Restart with new limits:
```bash
make restart
```

## 📊 Verification Checklist

After installation, verify:

- [ ] All services are running (`make status`)
- [ ] Production check passes (`make prod-check`)
- [ ] Grafana dashboard shows metrics
- [ ] Prometheus targets are up
- [ ] API health endpoint responds (`curl http://localhost:8010/health`)
- [ ] Workers are processing jobs
- [ ] Alerts are configured
- [ ] Backups are working (`make backup`)
- [ ] Logs are in JSON format
- [ ] Strong passwords are set

## 🐛 Troubleshooting Installation

### Issue: Monitoring services not starting

```bash
# Check Docker logs
docker compose -p trading_bot logs prometheus grafana

# Common fix: Port conflicts
# Edit docker-compose.monitoring.yml and change ports
```

### Issue: Grafana dashboards not loading

```bash
# Verify dashboard file exists
ls -l config/grafana/dashboards/

# Verify provisioning config
cat config/grafana/provisioning/dashboards/dashboards.yml

# Restart Grafana
docker compose -p trading_bot restart grafana
```

### Issue: Metrics not appearing in Prometheus

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Check if services expose metrics
curl http://localhost:8010/metrics
curl http://localhost:9091/metrics

# Verify prometheus.yml configuration
cat config/prometheus/prometheus.yml
```

### Issue: Workers not exporting metrics

```bash
# Check worker logs
make logs service=worker

# Verify metrics port is not in use
docker exec trading_bot_worker_1 netstat -tulpn | grep 9091

# Restart workers
docker compose -p trading_bot restart worker
```

## 🔄 Rollback Procedure

If you need to rollback:

```bash
# 1. Stop monitoring services
docker compose -p trading_bot -f docker-compose.monitoring.yml down

# 2. Restore original service files
git checkout services/api/src/main.py
git checkout services/worker/src/worker.py

# 3. Rebuild images
make build

# 4. Restart with original configuration
make restart
```

## 📚 Next Steps

After successful installation:

1. Read [Production Guide](PRODUCTION.md)
2. Configure alert notifications
3. Set up automated backups
4. Review and customize dashboards
5. Train your team on new monitoring tools

## 🆘 Getting Help

If you encounter issues:

1. Check logs: `make logs service=<service>`
2. Run diagnostics: `make diag-full`
3. Review this guide
4. Check GitHub issues
5. Contact your team lead

## 📝 File Checklist

Make sure all these files are created:

### Configuration Files
- [ ] `docker-compose.monitoring.yml`
- [ ] `config/prometheus/prometheus.yml`
- [ ] `config/prometheus/alerts.yml`
- [ ] `config/alertmanager/alertmanager.yml`
- [ ] `config/grafana/provisioning/datasources/prometheus.yml`
- [ ] `config/grafana/provisioning/dashboards/dashboards.yml`
- [ ] `config/grafana/dashboards/trading-bot-dashboard.json`

### Code Files
- [ ] `services/api/src/middleware/metrics.py`
- [ ] `services/api/src/main_updated.py` (or update existing main.py)
- [ ] `services/worker/src/metrics.py`
- [ ] `services/worker/src/worker_enhanced.py` (or update existing worker.py)

### Scripts
- [ ] `scripts/setup-monitoring.sh`
- [ ] `scripts/production-check.sh`

### Documentation
- [ ] `docs/PRODUCTION.md`
- [ ] `docs/INSTALLATION.md`
- [ ] `.env.production.example`

### Makefile
- [ ] `Makefile.monitoring` (or add targets to existing Makefile)

---

**Installation Time**: 30-60 minutes  
**Difficulty**: Intermediate  
**Support**: operations@trading-bot.local