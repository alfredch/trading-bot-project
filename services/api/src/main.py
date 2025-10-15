#!/usr/bin/env python3
"""
FastAPI Service - ANGEPASST für TimescaleDB Schema
"""
import os
import sys
import logging
import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import redis

sys.path.insert(0, '/app')

# Import aus models package
from .models.schemas import (
    MigrationJobRequest,
    BacktestJobRequest,
    JobResponse,
    HealthResponse
)

# Rest bleibt gleich...
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Trading Bot API",
    version="1.0.0",
    description="API for trading bot operations"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'redis'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Trading Bot API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "jobs": "/jobs",
            "migrate": "/jobs/migrate",
            "backtest": "/jobs/backtest"
        }
    }


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check"""
    try:
        redis_client.ping()
        return HealthResponse(
            status="healthy",
            redis="connected",
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            redis=f"error: {str(e)}",
            timestamp=datetime.utcnow().isoformat()
        )


@app.post("/jobs/migrate", response_model=JobResponse)
async def create_migration_job(request: MigrationJobRequest):
    """
    Create data migration job

    Migrates tick data from PostgreSQL to Parquet format
    """
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

        logger.info(f"Created migration job: {job_id}")

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
    """Create backtest job"""
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

        logger.info(f"Created backtest job: {job_id}")

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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)