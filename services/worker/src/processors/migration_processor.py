"""
Migration job processor - ANGEPASST FÜR TIMESCALEDB
"""
import logging
import json
from typing import Dict, Any
from .base_processor import BaseProcessor

logger = logging.getLogger(__name__)


class MigrationProcessor(BaseProcessor):
    """Process migration jobs"""

    def process(self, job_id: str, job_info: Dict[str, Any]) -> bool:
        """
        Process migration job

        Args:
            job_id: Job identifier
            job_info: Job information with run_id, instrument_id

        Returns:
            True if successful
        """
        try:
            # Parse job info
            run_id = int(job_info.get('run_id'))
            instrument_id = int(job_info.get('instrument_id'))
            config = json.loads(job_info.get('config', '{}'))

            start_date = config.get('start_date')
            end_date = config.get('end_date')
            chunk_size = config.get('chunk_size', 1000000)

            logger.info(
                f"Starting migration: RUN{run_id}/INST{instrument_id}, "
                f"{start_date} to {end_date}"
            )

            # Import pipeline components
            from src.config import WorkerConfig
            from data_pipeline.src.loader import OptimizedTickDataLoader
            from data_pipeline.src.converter import ParquetConverter
            from pathlib import Path

            # Initialize loader
            db_config = WorkerConfig.get_db_config()
            db_config['schema'] = 'trading_schema'  # Add schema

            loader = OptimizedTickDataLoader(
                db_config=db_config,
                chunk_size=chunk_size
            )

            # Initialize converter
            converter = ParquetConverter(
                output_dir=Path(WorkerConfig.DATA_PATH)
            )

            # Process chunks
            total_rows = 0
            chunk_count = 0

            for chunk_idx, df_chunk in enumerate(
                loader.stream_from_postgres(
                    run_id=run_id,
                    instrument_id=instrument_id,
                    start_date=start_date,
                    end_date=end_date
                )
            ):
                # Convert to Nautilus schema
                df_nautilus = converter.to_nautilus_schema(
                    df_chunk,
                    run_id,
                    instrument_id
                )

                # Write to Parquet
                converter.write_parquet_partitioned(
                    df_nautilus,
                    run_id,
                    instrument_id,
                    chunk_idx
                )

                total_rows += len(df_chunk)
                chunk_count += 1

                # Update progress
                progress = min(95, (chunk_count * 10))
                self.update_progress(
                    job_id,
                    progress,
                    f"Processed {total_rows:,} rows ({chunk_count} chunks)"
                )

                logger.info(f"Chunk {chunk_count}: {len(df_chunk):,} rows")

            logger.info(
                f"Migration complete: {total_rows:,} rows in {chunk_count} chunks"
            )

            # Store result
            result = {
                'total_rows': total_rows,
                'chunks': chunk_count,
                'run_id': run_id,
                'instrument_id': instrument_id
            }
            self.redis.hset(f"job:{job_id}", 'result', json.dumps(result))

            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}", exc_info=True)
            return False