# Production Deployment Guide

This guide covers deploying and operating the Trading Bot system in a production environment.

## 🚀 Quick Start

```bash
# 1. Setup production environment
cp .env.production.example .env
# Edit .env with your production values

# 2. Setup monitoring
make monitoring-setup

# 3. Start core services
make start

# 4. Start workers
make start-workers

# 5. Verify production readiness
make prod-check
```

## 📊 Monitoring & Observability

### Access Dashboards

- **Grafana**: http://localhost:3000 (admin/your-password)
- **Prometheus**: http://localhost:9090
- **AlertManager**: http://localhost:9093

### Key Metrics

```bash
# View API metrics
make metrics-api

# View worker metrics
make metrics-worker

# Full system diagnostics
make diag-full

# Performance metrics
make diag-performance
```

### Grafana Dashboards

The main dashboard shows:
- Active workers and job queue status
- Job processing rates and durations
- API latency (p50, p95, p99)
- System resources (CPU, memory, disk)
- Database and Redis metrics

## 🔔 Alerting

### Configured Alerts

1. **Critical Alerts** (immediate action required)
   - ServiceDown: Any service is down for >1 minute
   - PostgresDown: Database connection failed
   - RedisDown: Cache unavailable
   - NoWorkersAvailable: All workers stopped

2. **Warning Alerts** (attention needed)
   - HighErrorRate: >5% error rate for 5 minutes
   - WorkerQueueBacklog: >100 pending jobs for 5 minutes
   - HighDatabaseConnections: >180/200 connections
   - RedisMemoryHigh: >90% memory usage
   - DeadLetterQueueGrowing: >10 failed jobs in DLQ

3. **Info Alerts** (informational)
   - HighAPIRequestRate: Unusual traffic spike

### Managing Alerts

```bash
# List active alerts
make alerts-list

# Silence an alert for 1 hour
make alerts-silence alert=HighErrorRate

# View alert history in Grafana
# Navigate to: Alerting → Alert Rules
```

### Configure Notifications

Edit `config/alertmanager/alertmanager.yml`:

```yaml
receivers:
  - name: 'critical'
    # Email
    email_configs:
      - to: 'ops@your-domain.com'
    
    # Slack
    slack_configs:
      - api_url: 'YOUR_WEBHOOK_URL'
        channel: '#alerts'
    
    # PagerDuty
    pagerduty_configs:
      - service_key: 'YOUR_SERVICE_KEY'
```

## 🔒 Security Best Practices

### 1. Strong Passwords

Generate secure passwords:
```bash
# Generate password
openssl rand -base64 32

# Update .env
POSTGRES_PASSWORD=<generated_password>
REDIS_PASSWORD=<generated_password>
GRAFANA_ADMIN_PASSWORD=<generated_password>
```

### 2. Network Security

```bash
# Bind services to localhost only in production
POSTGRES_HOST_PORT=127.0.0.1:5432
REDIS_HOST_PORT=127.0.0.1:6380
API_HOST_PORT=127.0.0.1:8010
```

### 3. TLS/SSL (Recommended)

For external access, use nginx as reverse proxy with SSL:

```bash
# Add to docker-compose.yml
nginx:
  image: nginx:alpine
  volumes:
    - ./config/nginx/nginx.conf:/etc/nginx/nginx.conf
    - ./certs:/etc/nginx/certs
  ports:
    - "443:443"
```

## 📈 Performance Optimization

### 1. Worker Scaling

```bash
# Scale workers based on load
make scale workers=8

# Monitor queue length to determine optimal worker count
# Rule of thumb: 1 worker per 10-20 pending jobs
```

### 2. Database Tuning

For production workloads, tune PostgreSQL settings in `.env`:

```bash
# For 32GB RAM system
POSTGRES_SHARED_BUFFERS=8GB
POSTGRES_EFFECTIVE_CACHE_SIZE=24GB
POSTGRES_WORK_MEM=256MB
POSTGRES_MAINTENANCE_WORK_MEM=2GB
```

### 3. Redis Optimization

```bash
# Increase Redis memory limit for caching
REDIS_MAXMEMORY=8gb

# Adjust eviction policy if needed
# In redis.conf: maxmemory-policy allkeys-lru
```

### 4. API Performance

```bash
# Increase API workers for high traffic
API_WORKERS=8

# Enable connection pooling (already configured)
# See services/api/src/main_updated.py
```

## 💾 Backup & Recovery

### Automated Backups

```bash
# Manual backup
make backup

# Automated daily backup (add to crontab)
0 2 * * * cd /path/to/trading-bot-project && make backup
```

### Backup Contents

- PostgreSQL database dump
- Redis snapshot (RDB)
- Configuration files
- Parquet data files (optional, large)

### Restore from Backup

```bash
# List available backups
ls -lh data/backups/

# Restore specific backup
make restore backup=backup_20250115_020000.tar.gz
```

### Backup Retention

Edit `.env`:
```bash
BACKUP_RETENTION_DAYS=30  # Keep backups for 30 days
```

Cleanup old backups automatically:
```bash
# Add to crontab for weekly cleanup
0 3 * * 0 cd /path/to/trading-bot-project && make cleanup-backups
```

## 🔍 Troubleshooting

### Service Health Issues

```bash
# Check service status
make status

# View logs for specific service
make logs service=api
make logs service=worker
make logs service=postgres

# Check health endpoints
curl http://localhost:8010/health | jq
```

### High Error Rates

```bash
# View recent errors
make diag-errors

# Check failed jobs in Dead Letter Queue
make dlq-list

# Retry failed job
make dlq-retry job_id=<job_id>
```

### Performance Issues

```bash
# Check system resources
make diag-performance

# View worker metrics
docker stats | grep worker

# Check database slow queries
docker exec trading_bot_postgres psql -U trading_bot -c "SELECT query, calls, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

### Worker Not Processing Jobs

```bash
# Check worker logs
make logs service=worker

# Check worker heartbeats
make worker-heartbeats

# Restart workers
docker compose -p trading_bot restart worker

# Check Redis connection
docker exec trading_bot_redis redis-cli ping
```

### Database Connection Issues

```bash
# Check PostgreSQL status
docker exec trading_bot_postgres pg_isready

# Check active connections
docker exec trading_bot_postgres psql -U trading_bot -c "SELECT count(*) FROM pg_stat_activity;"

# Check for locks
docker exec trading_bot_postgres psql -U trading_bot -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

## 📊 Capacity Planning

### Monitoring Resource Usage

```bash
# View resource usage trends in Grafana
# Navigate to: System Resources Dashboard

# Current resource usage
make diag-full
```

### Scaling Guidelines

| Metric | Threshold | Action |
|--------|-----------|--------|
| Queue Length | >100 jobs | Scale workers up |
| Worker CPU | >80% sustained | Add workers or increase CPU limit |
| Worker Memory | >85% | Increase memory limit or reduce concurrency |
| Database Connections | >160/200 | Optimize queries or increase max_connections |
| Redis Memory | >80% | Increase maxmemory or review caching strategy |
| API Latency p95 | >2s | Scale API workers or optimize endpoints |
| Disk Usage | >80% | Archive old data or expand storage |

### Vertical Scaling (Single Server)

Edit `.env` for larger resources:

```bash
# For 64GB RAM, 16 CPU cores
WORKER_REPLICAS=8
WORKER_MEMORY_LIMIT=6gb
POSTGRES_SHARED_BUFFERS=16GB
REDIS_MAXMEMORY=8gb
```

### Horizontal Scaling (Multi-Server)

For multi-server deployments:

1. **Database**: Use managed PostgreSQL (AWS RDS, Azure Database)
2. **Redis**: Use Redis Cluster or managed Redis
3. **Workers**: Deploy on multiple servers, all connecting to central Redis
4. **API**: Load balance multiple API instances

## 🔄 Updates & Maintenance

### Rolling Updates

```bash
# 1. Pull latest changes
git pull origin main

# 2. Build new images
make build

# 3. Update one service at a time
docker compose -p trading_bot up -d --no-deps api
docker compose -p trading_bot up -d --no-deps worker

# 4. Verify health
make health
```

### Zero-Downtime Deployment

```bash
# 1. Scale up workers before update
make scale workers=6

# 2. Update half of workers
docker compose -p trading_bot up -d --no-deps --scale worker=3 worker

# 3. Wait and verify
sleep 30
make health

# 4. Update remaining workers
docker compose -p trading_bot up -d --scale worker=6 worker
```

### Database Migrations

```bash
# 1. Backup before migration
make backup

# 2. Run migration
make migrate

# 3. Verify migration
docker exec trading_bot_postgres psql -U trading_bot -c "\dt"
```

## 📝 Logging Best Practices

### Log Levels

- **ERROR**: System failures requiring immediate attention
- **WARNING**: Potential issues or degraded performance
- **INFO**: Normal operations and important events
- **DEBUG**: Detailed information for troubleshooting (dev only)

### Production Logging

```bash
# Set in .env
LOG_LEVEL=INFO
LOG_FORMAT=json

# View structured logs
make logs service=api | jq 'select(.levelname=="ERROR")'
```

### Log Aggregation

For production, consider centralizing logs:

```bash
# Example: Send to Elasticsearch/Loki
docker compose -f docker-compose.yml -f docker-compose.logging.yml up -d
```

### Log Rotation

Configure in `docker-compose.yml`:

```yaml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

## 🎯 SLAs & Monitoring

### Recommended SLAs

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| API Uptime | 99.9% | <99.5% |
| API Response Time (p95) | <1s | >2s |
| Job Success Rate | >98% | <95% |
| Job Processing Time | <5min avg | >10min avg |
| Worker Availability | >2 active | <2 active |
| Database Response Time | <100ms | >500ms |

### Custom Metrics

Add custom metrics in your code:

```python
from prometheus_client import Counter, Histogram

custom_metric = Counter('custom_operations_total', 'Custom operations')
custom_metric.inc()
```

## 🚨 Incident Response

### 1. Alert Received

```bash
# Quick diagnostics
make diag-full

# Check specific service
make logs service=<service>
```

### 2. Identify Issue

- Check Grafana dashboards for anomalies
- Review recent deployments or changes
- Check system resources
- Review error logs

### 3. Mitigation

```bash
# Restart unhealthy service
docker compose -p trading_bot restart <service>

# Scale workers if queue backing up
make scale workers=8

# Clear stuck jobs (if safe)
docker exec trading_bot_redis redis-cli DEL queue:migration
```

### 4. Resolution

- Fix root cause
- Deploy fix using rolling update
- Verify fix with monitoring
- Document incident

## 📞 Support & Maintenance Contacts

### Regular Maintenance Schedule

- **Daily**: Check dashboards, review alerts
- **Weekly**: Review DLQ, check backups, analyze trends
- **Monthly**: Capacity planning, performance review
- **Quarterly**: Security updates, dependency updates

### Emergency Contacts

Document your team's contact information:

```yaml
# contacts.yml
on_call:
  primary: "ops-primary@your-domain.com"
  secondary: "ops-secondary@your-domain.com"
  
escalation:
  - level: 1
    contact: "team-lead@your-domain.com"
  - level: 2
    contact: "engineering-manager@your-domain.com"
```

## 🔐 Compliance & Audit

### Audit Logging

All job operations are logged with:
- Job ID
- Worker ID
- Timestamp
- Status changes
- Error messages

Query audit trail:
```bash
# View job history
curl http://localhost:8010/jobs?limit=100 | jq

# Search logs for specific job
make logs | grep "job_id=<job_id>"
```

### Data Retention

Configure retention policies in `.env`:

```bash
# Parquet data retention
DATA_RETENTION_DAYS=365

# Log retention
LOG_RETENTION_DAYS=90

# Job history in Redis
JOB_HISTORY_RETENTION_DAYS=30
```

## 🎓 Training & Onboarding

### For Operators

1. Review this production guide
2. Complete production readiness check: `make prod-check`
3. Practice common operations:
   - View dashboards
   - Respond to alerts
   - Scale workers
   - Check logs
   - Run backups

### For Developers

1. Review code structure in project README
2. Understand metrics and instrumentation
3. Learn debugging techniques
4. Practice local development workflow

## 📚 Additional Resources

- **Main README**: `../README.md`
- **API Documentation**: http://localhost:8010/docs
- **Prometheus Queries**: http://localhost:9090/graph
- **Grafana Dashboards**: http://localhost:3000
- **Alert Rules**: `config/prometheus/alerts.yml`

## 🆘 Getting Help

1. Check this guide first
2. Review logs: `make logs service=<service>`
3. Run diagnostics: `make diag-full`
4. Check GitHub issues: https://github.com/alfredch/trading-bot-project/issues
5. Contact team leads

---

**Last Updated**: 2025-01-15  
**Version**: 1.0.0  
**Maintained By**: Trading Bot Operations Team