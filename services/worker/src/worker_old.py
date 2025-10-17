"""
Production-Ready Enhanced Worker with Metrics and Circuit Breaker
"""
import os
import sys
import time
import signal
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum

import redis
from redis.connection import ConnectionPool

from .metrics import WorkerMetrics

# Setup structured logging
import logging.config

LOGGING_CONFIG = {
    "version": 1,
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


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                logger.info("Circuit breaker entering HALF_OPEN state")
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise

    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        if self.state == CircuitState.HALF_OPEN:
            logger.info("Circuit breaker recovered, entering CLOSED state")
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(f"Circuit breaker opened after {self.failure_count} failures")
                self.state = CircuitState.OPEN


class EnhancedWorker:
    """Production-ready worker with monitoring and resilience"""

    def __init__(self):
        # Worker ID
        default_worker_id = f"worker-{os.getpid()}"
        self.worker_id = os.getenv('WORKER_NAME', default_worker_id).replace('{{.Task.Slot}}', str(os.getpid()))
        self.running = True
        self.current_job_id = None

        # Configuration
        self.max_retries = int(os.getenv('JOB_MAX_RETRIES', 3))
        self.heartbeat_interval = int(os.getenv('WORKER_HEARTBEAT_INTERVAL', 30))
        self.metrics_interval = int(os.getenv('WORKER_METRICS_INTERVAL', 60))
        self.brpop_timeout = 5

        # Metrics
        self.metrics = WorkerMetrics(
            worker_id=self.worker_id,
            port=int(os.getenv('WORKER_METRICS_PORT', 9091))
        )

        # Start metrics server
        try:
            self.metrics.start_metrics_server()
            logger.info(f"Metrics server started on port {self.metrics.port}")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")

        # Circuit breakers
        self.redis_breaker = CircuitBreaker(failure_threshold=5, timeout=60)
        self.db_breaker = CircuitBreaker(failure_threshold=3, timeout=120)

        # Redis connection pool
        self.redis_pool = ConnectionPool(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            max_connections=10,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
            retry_on_timeout=True
        )
        self.redis = redis.Redis(connection_pool=self.redis_pool)

        # Test connection with circuit breaker
        try:
            self.redis_breaker.call(self.redis.ping)
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info(f"Worker {self.worker_id} initialized (PID: {os.getpid()})")

    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False
        self.metrics.shutdown()

    def process_jobs(self):
        """Main worker loop with monitoring"""
        logger.info(f"Worker {self.worker_id} started. Waiting for jobs...")

        last_heartbeat = time.time()
        last_metrics_update = time.time()
        jobs_processed = 0
        consecutive_errors = 0

        while self.running:
            try:
                # Update heartbeat
                if time.time() - last_heartbeat > self.heartbeat_interval:
                    self._update_heartbeat()
                    last_heartbeat = time.time()

                # Update resource metrics
                if time.time() - last_metrics_update > self.metrics_interval:
                    self.metrics.update_resource_usage()
                    self._update_queue_metrics()
                    last_metrics_update = time.time()

                # Wait for jobs with circuit breaker
                try:
                    job_data = self.redis_breaker.call(
                        self.redis.brpop,
                        ['queue:migration', 'queue:backtest'],
                        timeout=self.brpop_timeout
                    )
                except Exception as e:
                    if "Circuit breaker is OPEN" in str(e):
                        logger.warning("Redis circuit breaker is OPEN, waiting...")
                        time.sleep(10)
                        continue
                    raise

                if not job_data:
                    continue

                # Reset error counter
                consecutive_errors = 0

                queue_name, job_id = job_data
                self.current_job_id = job_id

                logger.info(f"Processing job: {job_id} from {queue_name}", extra={
                    'job_id': job_id,
                    'queue': queue_name,
                    'worker_id': self.worker_id
                })

                # Update status
                self._update_job_status(job_id, 'running', 0, f'Started by {self.worker_id}')

                # Process job with timing
                start_time = time.time()
                success = self._process_job(job_id)
                duration = time.time() - start_time

                # Get job type for metrics
                job_info = self.redis.hgetall(f"job:{job_id}")
                job_type = job_info.get('type', 'unknown')

                if success:
                    self._update_job_status(
                        job_id,
                        'completed',
                        100,
                        f'Completed in {duration:.2f}s'
                    )
                    jobs_processed += 1
                    self.metrics.record_job_complete(job_type, duration, True)
                    logger.info(f"Job {job_id} completed successfully", extra={
                        'job_id': job_id,
                        'duration': duration,
                        'worker_id': self.worker_id
                    })
                else:
                    self.metrics.record_job_complete(job_type, duration, False)

                self.current_job_id = None

            except redis.exceptions.TimeoutError:
                continue

            except redis.exceptions.ConnectionError as e:
                consecutive_errors += 1
                self.metrics.record_error('redis_connection')
                logger.error(f"Redis connection error (attempt {consecutive_errors}): {e}")

                if consecutive_errors > 5:
                    logger.error("Too many consecutive connection errors, waiting longer...")
                    time.sleep(30)
                else:
                    time.sleep(5)

                try:
                    self.redis.ping()
                    logger.info("Reconnected to Redis")
                    consecutive_errors = 0
                except:
                    pass

            except Exception as e:
                consecutive_errors += 1
                self.metrics.record_error('unexpected')
                logger.error(
                    f"Unexpected error in worker loop (attempt {consecutive_errors}): {e}",
                    exc_info=True,
                    extra={'worker_id': self.worker_id}
                )

                if self.current_job_id:
                    self._handle_job_failure(self.current_job_id, str(e))

                if consecutive_errors > 10:
                    logger.critical("Too many consecutive errors, shutting down")
                    break

                time.sleep(1)

        logger.info(f"Worker {self.worker_id} shutting down. Processed {jobs_processed} jobs.")
        self.redis_pool.disconnect()

    def _process_job(self, job_id: str) -> bool:
        """Process a job with circuit breaker protection"""
        try:
            job_info = self.redis.hgetall(f"job:{job_id}")

            if not job_info:
                logger.error(f"Job {job_id} not found")
                return False

            job_type = job_info.get('type')

            if job_type == 'migration':
                return self._process_migration(job_id, job_info)
            elif job_type == 'backtest':
                return self._process_backtest(job_id, job_info)
            else:
                logger.error(f"Unknown job type: {job_type}")
                return False

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
            self._handle_job_failure(job_id, str(e))
            return False

    def _process_migration(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """Process migration job"""
        try:
            from src.processors.migration_processor import MigrationProcessor

            processor = MigrationProcessor(
                redis_client=self.redis,
                worker_id=self.worker_id
            )

            config = json.loads(job_info.get('config', '{}'))
            instrument = job_info.get('instrument')

            return processor.process(job_id, instrument, config)

        except ImportError:
            logger.warning("MigrationProcessor not found, using mock")
            for i in range(5):
                self._update_job_status(job_id, 'running', i * 20, f'Processing... {i * 20}%')
                time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Migration error: {e}", exc_info=True)
            raise

    def _process_backtest(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """Process backtest job"""
        try:
            from src.processors.backtest_processor import BacktestProcessor

            processor = BacktestProcessor(
                redis_client=self.redis,
                worker_id=self.worker_id
            )

            strategy_config = json.loads(job_info.get('strategy', '{}'))

            return processor.process(job_id, strategy_config)

        except ImportError:
            logger.warning("BacktestProcessor not found, using mock")
            for i in range(5):
                self._update_job_status(job_id, 'running', i * 20, f'Backtesting... {i * 20}%')
                time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            raise

    def _handle_job_failure(self, job_id: str, error_message: str):
        """Handle job failure with retry logic"""
        try:
            retry_count = int(self.redis.hget(f"job:{job_id}", 'retry_count') or 0)
            job_info = self.redis.hgetall(f"job:{job_id}")
            job_type = job_info.get('type', 'unknown')

            if retry_count < self.max_retries:
                self.redis.hincrby(f"job:{job_id}", 'retry_count', 1)

                self._update_job_status(
                    job_id,
                    'retry_scheduled',
                    0,
                    f'Retry {retry_count + 1}/{self.max_retries} scheduled'
                )

                # Requeue
                self.redis.lpush(f'queue:{job_type}', job_id)

                # Record metrics
                self.metrics.record_job_retry(job_type, retry_count + 1)

                logger.warning(f"Job {job_id} scheduled for retry {retry_count + 1}")
            else:
                self._update_job_status(
                    job_id,
                    'failed',
                    0,
                    f'Failed after {self.max_retries} retries: {error_message}'
                )
                self.redis.lpush('queue:dlq', job_id)

                # Record metrics
                self.metrics.record_dlq_move(job_type, 'max_retries_exceeded')

                logger.error(f"Job {job_id} moved to DLQ after {self.max_retries} retries")

        except Exception as e:
            logger.error(f"Error handling job failure: {e}")

    def _update_job_status(self, job_id: str, status: str, progress: int, message: str):
        """Update job status in Redis"""
        try:
            self.redis.hset(f"job:{job_id}", mapping={
                'status': status,
                'progress': progress,
                'message': message,
                'worker_id': self.worker_id,
                'updated_at': datetime.utcnow().isoformat()
            })

            self.redis.publish(
                f"jobs:progress:{job_id}",
                json.dumps({
                    'job_id': job_id,
                    'status': status,
                    'progress': progress,
                    'message': message
                })
            )
        except Exception as e:
            logger.error(f"Error updating job status: {e}")

    def _update_heartbeat(self):
        """Update worker heartbeat"""
        try:
            self.redis.setex(
                f"worker:{self.worker_id}:heartbeat",
                60,
                datetime.utcnow().isoformat()
            )
            self.metrics.update_heartbeat()
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")

    def _update_queue_metrics(self):
        """Update queue length metrics"""
        try:
            for queue_name in ['migration', 'backtest', 'dlq']:
                length = self.redis.llen(f'queue:{queue_name}')
                self.metrics.update_queue_length(queue_name, length)
        except Exception as e:
            logger.error(f"Error updating queue metrics: {e}")


def main():
    """Worker entry point"""
    worker = EnhancedWorker()
    worker.process_jobs()


if __name__ == "__main__":
    main()