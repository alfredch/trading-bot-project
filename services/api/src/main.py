#!/usr/bin/env python3
"""
FastAPI Service - Production-Ready Version mit Monitoring
"""
import os
import sys
import logging
import json
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import redis
from redis.connection import ConnectionPool

sys.path.insert(0, '/app')

from .models.schemas import (
    MigrationJobRequest,
    BacktestJobRequest,
    JobResponse,
    HealthResponse
)
from .middleware.metrics import (
    MetricsMiddleware,
    metrics_endpoint,
    record_job_submission,
    record_redis_operation
)

# Structured logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        },
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json" if os.getenv("LOG_FORMAT") == "json" else "standard",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": os.getenv("LOG_LEVEL", "INFO"),
        "handlers": ["console"]
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)


# Lifespan context for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info("Starting Trading Bot API...")

    # Initialize Redis connection pool
    global redis_pool, redis_client
    redis_pool = ConnectionPool(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        max_connections=50,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=5,
        retry_on_timeout=True
    )
    redis_client = redis.Redis(connection_pool=redis_pool)

    # Test connection
    try:
        redis_client.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

    yield

    # Cleanup
    logger.info("Shutting down Trading Bot API...")
    redis_pool.disconnect()


app = FastAPI(
    title="Trading Bot API",
    version=os.getenv('PROJECT_VERSION', '1.0.0'),
    description="Production-ready API for trading bot operations",
    lifespan=lifespan
)

# Add middlewares
app.add_middleware(MetricsMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis client placeholder
redis_client = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Trading Bot API",
        "version": os.getenv('PROJECT_VERSION', '1.0.0'),
        "status": "running",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
            "jobs": "/jobs",
            "migrate": "/jobs/migrate",
            "backtest": "/jobs/backtest",
            "alerts": "/alerts/webhook"
        }
    }


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return metrics_endpoint()


@app.get("/health", response_model=HealthResponse)
async def health():
    """Enhanced health check with detailed status"""
    import time
    start = time.time()

    health_status = {
        "status": "healthy",
        "redis": "unknown",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # Check Redis
    try:
        redis_start = time.time()
        redis_client.ping()
        redis_duration = time.time() - redis_start
        health_status["redis"] = "connected"
        health_status["checks"]["redis"] = {
            "status": "ok",
            "response_time_ms": round(redis_duration * 1000, 2)
        }
        record_redis_operation("health_check", redis_duration, True)
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status["status"] = "degraded"
        health_status["redis"] = f"error: {str(e)}"
        health_status["checks"]["redis"] = {
            "status": "error",
            "error": str(e)
        }
        record_redis_operation("health_check", 0, False)

    # Check queue lengths
    try:
        migration_queue = redis_client.llen('queue:migration')
        backtest_queue = redis_client.llen('queue:backtest')
        dlq_length = redis_client.llen('queue:dlq')

        health_status["checks"]["queues"] = {
            "migration": migration_queue,
            "backtest": backtest_queue,
            "dead_letter": dlq_length
        }

        if dlq_length > 50:
            health_status["status"] = "degraded"
            health_status["checks"]["queues"]["warning"] = "High DLQ length"

    except Exception as e:
        logger.error(f"Queue check failed: {e}")

    # Total health check duration
    health_status["health_check_duration_ms"] = round((time.time() - start) * 1000, 2)

    return health_status


@app.post("/jobs/migrate", response_model=JobResponse)
async def create_migration_job(request: MigrationJobRequest):
    """Create data migration job with metrics"""
    try:
        job_id = f"migration:run{request.run_id}_inst{request.instrument_id}:{int(datetime.utcnow().timestamp())}"

        job_data = {
            'job_id': job_id,
            'type': 'migration',
            'run_id': str(request.run_id),
            'instrument_id': str(request.instrument_id),
            'config': json.dumps({
                'start_date': request.start_date,
                'end_date': request.end_date,
                'chunk_size': request.chunk_size
            }),
            'status': 'queued',
            'progress': 0,
            'message': 'Job queued',
            'created_at': datetime.utcnow().isoformat()
        }

        redis_client.hset(f"job:{job_id}", mapping=job_data)
        redis_client.lpush('queue:migration', job_id)
        redis_client.publish('jobs:new', json.dumps(job_data))

        # Record metrics
        record_job_submission('migration')

        logger.info(f"Created migration job: {job_id}", extra={
            'job_id': job_id,
            'job_type': 'migration',
            'run_id': request.run_id,
            'instrument_id': request.instrument_id
        })

        return JobResponse(
            job_id=job_id,
            status="queued",
            message=f"Migration job for RUN{request.run_id}/INST{request.instrument_id} created"
        )

    except Exception as e:
        logger.error(f"Error creating migration job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/jobs/backtest", response_model=JobResponse)
async def create_backtest_job(request: BacktestJobRequest):
    """Create backtest job with metrics"""
    try:
        job_id = f"backtest:{request.strategy_name}:run{request.run_id}_inst{request.instrument_id}:{int(datetime.utcnow().timestamp())}"

        job_data = {
            'job_id': job_id,
            'type': 'backtest',
            'strategy': json.dumps({
                'name': request.strategy_name,
                'run_id': request.run_id,
                'instrument_id': request.instrument_id,
                'start_date': request.start_date,
                'end_date': request.end_date,
                'config': request.config
            }),
            'status': 'queued',
            'progress': 0,
            'message': 'Job queued',
            'created_at': datetime.utcnow().isoformat()
        }

        redis_client.hset(f"job:{job_id}", mapping=job_data)
        redis_client.lpush('queue:backtest', job_id)
        redis_client.publish('jobs:new', json.dumps(job_data))

        # Record metrics
        record_job_submission('backtest')

        logger.info(f"Created backtest job: {job_id}", extra={
            'job_id': job_id,
            'job_type': 'backtest',
            'strategy': request.strategy_name
        })

        return JobResponse(
            job_id=job_id,
            status="queued",
            message=f"Backtest job created"
        )

    except Exception as e:
        logger.error(f"Error creating backtest job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """Get job status"""
    try:
        job_data = redis_client.hgetall(f"job:{job_id}")

        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")

        return job_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/jobs")
async def list_jobs(limit: int = 10, job_type: Optional[str] = None):
    """List recent jobs"""
    try:
        job_keys = redis_client.keys("job:*")

        jobs = []
        for key in job_keys:
            job_data = redis_client.hgetall(key)
            if job_type is None or job_data.get('type') == job_type:
                jobs.append(job_data)

        jobs.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return {
            'jobs': jobs[:limit],
            'total': len(jobs)
        }

    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/webhook")
async def alert_webhook(request: Request):
    """Webhook endpoint for AlertManager"""
    try:
        alert_data = await request.json()

        # Log alert
        logger.warning(
            f"Received alert: {alert_data.get('status')} - {alert_data.get('commonLabels', {}).get('alertname')}",
            extra={
                'alert_status': alert_data.get('status'),
                'alert_name': alert_data.get('commonLabels', {}).get('alertname')
            }
        )

        # Store alert in Redis for dashboard
        alerts = alert_data.get('alerts', [])
        for alert in alerts:
            alert_key = f"alert:{alert.get('labels', {}).get('alertname')}:{int(datetime.utcnow().timestamp())}"
            redis_client.setex(
                alert_key,
                86400,  # 24h TTL
                json.dumps(alert)
            )

        return {"status": "ok", "alerts_received": len(alerts)}

    except Exception as e:
        logger.error(f"Error processing alert webhook: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts")
async def list_alerts(limit: int = 20):
    """List recent alerts"""
    try:
        alert_keys = redis_client.keys("alert:*")
        alerts = []

        for key in alert_keys[-limit:]:
            alert_data = redis_client.get(key)
            if alert_data:
                alerts.append(json.loads(alert_data))

        return {"alerts": alerts, "total": len(alert_keys)}

    except Exception as e:
        logger.error(f"Error listing alerts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/jobs/{job_id}")
async def delete_job(job_id: str):
    """Delete a job from Redis"""
    try:
        # Delete job data
        deleted = redis_client.delete(f"job:{job_id}")

        if deleted:
            logger.info(f"Deleted job: {job_id}")
            return {"status": "ok", "message": f"Job {job_id} deleted"}
        else:
            raise HTTPException(status_code=404, detail="Job not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        # Queue lengths
        migration_queue = redis_client.llen('queue:migration')
        backtest_queue = redis_client.llen('queue:backtest')
        dlq_length = redis_client.llen('queue:dlq')

        # Worker heartbeats
        worker_keys = redis_client.keys('worker:*:heartbeat')
        active_workers = len(worker_keys)

        # Job counts
        job_keys = redis_client.keys('job:*')
        total_jobs = len(job_keys)

        # Count by status
        job_stats = {
            'queued': 0,
            'running': 0,
            'completed': 0,
            'failed': 0
        }

        for key in job_keys[:100]:  # Sample first 100
            job_data = redis_client.hgetall(key)
            status = job_data.get('status', 'unknown')
            if status in job_stats:
                job_stats[status] += 1

        return {
            'queues': {
                'migration': migration_queue,
                'backtest': backtest_queue,
                'dead_letter': dlq_length
            },
            'workers': {
                'active': active_workers
            },
            'jobs': {
                'total': total_jobs,
                **job_stats
            },
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_config=LOGGING_CONFIG
    )