"""
Prometheus Metrics Middleware for FastAPI
"""
import time
import os
from typing import Callable
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

# Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

# Job metrics
job_submissions_total = Counter(
    'job_submissions_total',
    'Total job submissions',
    ['job_type']
)

job_processing_duration_seconds = Histogram(
    'job_processing_duration_seconds',
    'Job processing duration',
    ['job_type', 'status'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

job_failures_total = Counter(
    'job_failures_total',
    'Total job failures',
    ['job_type', 'error_type']
)

# Redis metrics
redis_operations_total = Counter(
    'redis_operations_total',
    'Total Redis operations',
    ['operation', 'status']
)

redis_operation_duration_seconds = Histogram(
    'redis_operation_duration_seconds',
    'Redis operation duration',
    ['operation']
)

# Application metrics
app_info = Gauge(
    'app_info',
    'Application info',
    ['version', 'service']
)

# Set app info
app_info.labels(
    version=os.getenv('PROJECT_VERSION', '1.0.0'),
    service='api'
).set(1)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP metrics"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip metrics endpoint
        if request.url.path == '/metrics':
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        start_time = time.time()
        status_code = HTTP_500_INTERNAL_SERVER_ERROR

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response

        except Exception as e:
            # Log exception and re-raise
            raise

        finally:
            # Record metrics
            duration = time.time() - start_time

            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            http_requests_in_progress.labels(
                method=method,
                endpoint=endpoint
            ).dec()


def metrics_endpoint() -> Response:
    """Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


def record_job_submission(job_type: str):
    """Record job submission"""
    job_submissions_total.labels(job_type=job_type).inc()


def record_job_completion(job_type: str, status: str, duration: float):
    """Record job completion"""
    job_processing_duration_seconds.labels(
        job_type=job_type,
        status=status
    ).observe(duration)


def record_job_failure(job_type: str, error_type: str):
    """Record job failure"""
    job_failures_total.labels(
        job_type=job_type,
        error_type=error_type
    ).inc()


def record_redis_operation(operation: str, duration: float, success: bool):
    """Record Redis operation"""
    status = 'success' if success else 'error'
    redis_operations_total.labels(operation=operation, status=status).inc()
    redis_operation_duration_seconds.labels(operation=operation).observe(duration)