"""
Enhanced Worker with job processing
"""
import os
import sys
import time
import signal
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import redis

# Setup logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class EnhancedWorker:
    """Enhanced worker with retry logic and error handling"""

    def __init__(self):
        # Nutze Container-ID falls WORKER_NAME nicht gesetzt
        default_worker_id = f"worker-{os.getpid()}"
        self.worker_id = os.getenv('WORKER_NAME', default_worker_id).replace('{{.Task.Slot}}', str(os.getpid()))
        self.running = True
        self.current_job_id = None

        # Configuration
        self.max_retries = int(os.getenv('JOB_MAX_RETRIES', 3))
        self.heartbeat_interval = int(os.getenv('WORKER_HEARTBEAT_INTERVAL', 30))
        self.brpop_timeout = 5  # Sekunden

        # Redis connection mit angepassten Timeouts
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_timeout=None,  # Kein Socket-Timeout für BRPOP
            socket_connect_timeout=10,  # Nur beim Connect
            retry_on_timeout=False  # Kein Retry bei BRPOP Timeout
        )

        # Test connection
        try:
            self.redis.ping()
            logger.info("Redis connection established")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info(f"Worker {self.worker_id} initialized")

    def _handle_shutdown(self, signum, frame):
        """Graceful shutdown handler"""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False

    def process_jobs(self):
        """Main worker loop"""
        logger.info(f"Worker {self.worker_id} started. Waiting for jobs...")

        last_heartbeat = time.time()
        jobs_processed = 0
        consecutive_errors = 0

        while self.running:
            try:
                # Update heartbeat
                if time.time() - last_heartbeat > self.heartbeat_interval:
                    self._update_heartbeat()
                    last_heartbeat = time.time()

                # Wait for jobs - BRPOP blockiert bis Job verfügbar oder Timeout
                job_data = self.redis.brpop(
                    ['queue:migration', 'queue:backtest'],
                    timeout=self.brpop_timeout
                )

                if not job_data:
                    # Timeout - kein Job verfügbar, das ist normal!
                    continue

                # Reset error counter bei erfolgreichem Empfang
                consecutive_errors = 0

                queue_name, job_id = job_data
                self.current_job_id = job_id

                logger.info(f"Processing job: {job_id} from {queue_name}")

                # Update status
                self._update_job_status(job_id, 'running', 0, f'Started by {self.worker_id}')

                # Process job
                start_time = time.time()
                success = self._process_job(job_id)
                duration = time.time() - start_time

                if success:
                    self._update_job_status(
                        job_id,
                        'completed',
                        100,
                        f'Completed in {duration:.2f}s'
                    )
                    jobs_processed += 1
                    logger.info(f"Job {job_id} completed successfully in {duration:.2f}s")

                self.current_job_id = None

            except redis.exceptions.TimeoutError:
                # BRPOP Timeout ist NORMAL - einfach weiter warten
                continue

            except redis.exceptions.ConnectionError as e:
                consecutive_errors += 1
                logger.error(f"Redis connection error (attempt {consecutive_errors}): {e}")

                # Bei wiederholten Connection-Errors länger warten
                if consecutive_errors > 5:
                    logger.error("Too many consecutive connection errors, waiting longer...")
                    time.sleep(30)
                else:
                    time.sleep(5)

                # Versuche Reconnect
                try:
                    self.redis.ping()
                    logger.info("Reconnected to Redis")
                    consecutive_errors = 0
                except:
                    pass

            except Exception as e:
                consecutive_errors += 1
                logger.error(
                    f"Unexpected error in worker loop (attempt {consecutive_errors}): {e}",
                    exc_info=True
                )

                if self.current_job_id:
                    self._handle_job_failure(self.current_job_id, str(e))

                # Bei vielen Fehlern hintereinander längere Pause
                if consecutive_errors > 10:
                    logger.critical("Too many consecutive errors, shutting down")
                    break

                time.sleep(1)

        logger.info(f"Worker {self.worker_id} shutting down. Processed {jobs_processed} jobs.")

    def _process_job(self, job_id: str) -> bool:
        """Process a job"""
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
            # Mock implementation for testing
            for i in range(5):
                self._update_job_status(job_id, 'running', i * 20, f'Processing... {i*20}%')
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
            # Mock implementation for testing
            for i in range(5):
                self._update_job_status(job_id, 'running', i * 20, f'Backtesting... {i*20}%')
                time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            raise

    def _handle_job_failure(self, job_id: str, error_message: str):
        """Handle job failure"""
        try:
            retry_count = int(self.redis.hget(f"job:{job_id}", 'retry_count') or 0)

            if retry_count < self.max_retries:
                self.redis.hincrby(f"job:{job_id}", 'retry_count', 1)

                self._update_job_status(
                    job_id,
                    'retry_scheduled',
                    0,
                    f'Retry {retry_count + 1}/{self.max_retries} scheduled'
                )

                # Requeue
                job_info = self.redis.hgetall(f"job:{job_id}")
                job_type = job_info.get('type')
                self.redis.lpush(f'queue:{job_type}', job_id)

                logger.warning(f"Job {job_id} scheduled for retry {retry_count + 1}")
            else:
                self._update_job_status(
                    job_id,
                    'failed',
                    0,
                    f'Failed after {self.max_retries} retries: {error_message}'
                )
                self.redis.lpush('queue:dlq', job_id)
                logger.error(f"Job {job_id} moved to DLQ")

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
        except Exception as e:
            logger.error(f"Error updating heartbeat: {e}")