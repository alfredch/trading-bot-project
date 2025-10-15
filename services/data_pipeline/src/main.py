#!/usr/bin/env python3
"""
Data Pipeline Worker - Main Entry Point
"""
import sys
import os
import json
import time
import signal
import logging
from typing import Dict, Any
from datetime import datetime
from pathlib import Path

import redis

# Add app to path
sys.path.insert(0, '/app')

# Setup logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


class DataPipelineWorker:
    """Data pipeline worker"""

    def __init__(self):
        """Initialize worker"""
        self.running = True

        # Redis connection
        self.redis = redis.Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', 6379)),
            decode_responses=True,
            socket_timeout=None
        )

        # Import pipeline components
        from src.config import Config
        from src.loader import OptimizedTickDataLoader
        from src.converter import ParquetConverter

        config = Config()

        # Initialize loader
        self.loader = OptimizedTickDataLoader(
            db_config=config.get_db_config(),
            chunk_size=config.CHUNK_SIZE
        )

        # Initialize converter
        self.converter = ParquetConverter(
            output_dir=Path(config.PARQUET_PATH)
        )

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Data Pipeline Worker initialized")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False

    def process_jobs(self):
        """Main worker loop"""
        logger.info("Data Pipeline Worker started. Waiting for jobs...")

        while self.running:
            try:
                # Wait for migration jobs
                job_data = self.redis.brpop(['queue:migration'], timeout=5)

                if not job_data:
                    continue

                _, job_id = job_data

                logger.info(f"Processing job: {job_id}")

                # Get job info
                job_info = self.redis.hgetall(f"job:{job_id}")

                if not job_info:
                    logger.error(f"Job {job_id} not found in Redis")
                    continue

                # Update status
                self._update_job_status(job_id, 'running', 0, 'Starting migration...')

                # Process migration
                self.process_migration(job_id, job_info)

            except redis.exceptions.TimeoutError:
                # Normal - no job available
                continue

            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
                time.sleep(1)

        logger.info("Data Pipeline Worker shutting down")

    def process_migration(self, job_id: str, job_info: Dict[str, Any]):
        """Process migration job"""
        try:
            # Parse job info
            run_id = int(job_info.get('run_id'))
            instrument_id = int(job_info.get('instrument_id'))
            config = json.loads(job_info.get('config', '{}'))

            start_date = config.get('start_date')
            end_date = config.get('end_date')
            chunk_size = config.get('chunk_size', 1000000)

            logger.info(
                f"Migrating RUN{run_id}/INST{instrument_id} "
                f"from {start_date} to {end_date}"
            )

            total_rows = 0
            chunk_count = 0

            # Stream data from PostgreSQL
            for chunk_idx, df_chunk in enumerate(
                    self.loader.stream_from_postgres(
                        run_id=run_id,
                        instrument_id=instrument_id,
                        start_date=start_date,
                        end_date=end_date
                    )
            ):
                # Convert to Nautilus schema
                df_nautilus = self.converter.to_nautilus_schema(
                    df_chunk,
                    run_id,
                    instrument_id
                )

                # Write to Parquet
                self.converter.write_parquet_partitioned(
                    df_nautilus,
                    run_id,
                    instrument_id,
                    chunk_idx
                )

                total_rows += len(df_chunk)
                chunk_count += 1

                # Update progress
                progress = min(int((chunk_count) * 10), 95)
                self._update_job_status(
                    job_id,
                    'running',
                    progress,
                    f"Processed {total_rows:,} rows ({chunk_count} chunks)"
                )

                logger.info(f"Chunk {chunk_count}: {len(df_chunk):,} rows")

            logger.info(
                f"Migration complete: {total_rows:,} rows in {chunk_count} chunks"
            )

            # Final update
            self._update_job_status(
                job_id,
                'completed',
                100,
                f"Migration complete: {total_rows:,} rows"
            )

        except Exception as e:
            logger.error(f"Migration error: {e}", exc_info=True)
            self._update_job_status(
                job_id,
                'failed',
                0,
                f"Error: {str(e)}"
            )

    def _update_job_status(self, job_id: str, status: str, progress: int, message: str):
        """Update job status in Redis"""
        try:
            self.redis.hset(f"job:{job_id}", mapping={
                'status': status,
                'progress': progress,
                'message': message,
                'updated_at': datetime.now().isoformat()  # Fix deprecation warning
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


def main():
    """Main entry point"""
    try:
        worker = DataPipelineWorker()
        worker.process_jobs()
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()