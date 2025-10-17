"""
Prometheus Metrics for Worker Service
"""
import os
import time
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server

# Worker metrics
worker_active = Gauge(
    'worker_active',
    'Whether worker is active',
    ['worker_id']
)

worker_jobs_processed = Counter(
    'worker_jobs_processed_total',
    'Total jobs processed',
    ['worker_id', 'job_type', 'status']
)

worker_job_duration = Histogram(
    'worker_job_duration_seconds',
    'Job processing duration',
    ['worker_id', 'job_type'],
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600)
)

worker_errors = Counter(
    'worker_errors_total',
    'Total worker errors',
    ['worker_id', 'error_type']
)

worker_heartbeat = Gauge(
    'worker_heartbeat_timestamp',
    'Last heartbeat timestamp',
    ['worker_id']
)

# Queue metrics
queue_length = Gauge(
    'queue_length',
    'Current queue length',
    ['queue_name']
)

# Job-specific metrics
job_retries = Counter(
    'job_retries_total',
    'Total job retries',
    ['job_type', 'retry_count']
)

job_dlq_moves = Counter(
    'job_dlq_moves_total',
    'Jobs moved to dead letter queue',
    ['job_type', 'reason']
)

# Application info
worker_info = Info(
    'worker',
    'Worker information'
)


class WorkerMetrics:
    """Metrics collector for worker"""

    def __init__(self, worker_id: str, port: int = 9091):
        self.worker_id = worker_id
        self.port = port
        self.start_time = time.time()

        # Set worker info
        worker_info.info({
            'worker_id': worker_id,
            'version': os.getenv('PROJECT_VERSION', '1.0.0'),
            'service': 'worker'
        })

        # Mark worker as active
        worker_active.labels(worker_id=worker_id).set(1)

    def start_metrics_server(self):
        """Start metrics HTTP server"""
        try:
            start_http_server(self.port)
        except OSError as e:
            # Port might be in use, try next port
            self.port += 1
            start_http_server(self.port)

    def record_job_complete(self, job_type: str, duration: float, success: bool):
        """Record job completion"""
        status = 'success' if success else 'failed'

        worker_jobs_processed.labels(
            worker_id=self.worker_id,
            job_type=job_type,
            status=status
        ).inc()

        worker_job_duration.labels(
            worker_id=self.worker_id,
            job_type=job_type
        ).observe(duration)

    def record_error(self, error_type: str):
        """Record error"""
        worker_errors.labels(
            worker_id=self.worker_id,
            error_type=error_type
        ).inc()

    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        worker_heartbeat.labels(worker_id=self.worker_id).set(time.time())

    def update_queue_length(self, queue_name: str, length: int):
        """Update queue length"""
        queue_length.labels(queue_name=queue_name).set(length)

    def record_job_retry(self, job_type: str, retry_count: int):
        """Record job retry"""
        job_retries.labels(
            job_type=job_type,
            retry_count=str(retry_count)
        ).inc()

    def record_dlq_move(self, job_type: str, reason: str):
        """Record move to DLQ"""
        job_dlq_moves.labels(
            job_type=job_type,
            reason=reason
        ).inc()

    def shutdown(self):
        """Mark worker as inactive"""
        worker_active.labels(worker_id=self.worker_id).set(0)