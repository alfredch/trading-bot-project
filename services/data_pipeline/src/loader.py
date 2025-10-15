"""
Optimized data loader - ANGEPASST FÜR TIMESCALEDB SCHEMA
"""
import logging
from typing import Iterator, Dict, Any
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class OptimizedTickDataLoader:
    """
    Efficient loading of tick data from TimescaleDB
    """

    def __init__(self, db_config: Dict[str, Any], chunk_size: int = 1_000_000):
        """
        Initialize loader

        Args:
            db_config: PostgreSQL connection configuration (WITHOUT schema)
            chunk_size: Number of rows per chunk
        """
        self.db_config = db_config
        self.chunk_size = chunk_size
        # Schema wird separat gespeichert
        self.schema = 'trading_schema'  # Hardcoded oder aus ENV

    def stream_from_postgres(self,
                            run_id: int,
                            instrument_id: int,
                            start_date: str,
                            end_date: str) -> Iterator[pd.DataFrame]:
        """
        Stream data from PostgreSQL in chunks

        Args:
            run_id: Run ID (z.B. 24)
            instrument_id: Instrument ID (z.B. 651)
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Yields:
            DataFrame chunks
        """
        conn = None
        cursor = None

        try:
            # Connect to PostgreSQL - OHNE schema Parameter
            conn = psycopg2.connect(**self.db_config)

            # Server-side cursor for memory efficiency
            cursor = conn.cursor(
                name='tick_stream_cursor',
                cursor_factory=RealDictCursor
            )

            # Query mit Schema-Prefix
            query = f"""
                SELECT 
                    time,
                    run_id,
                    instrument_id,
                    price,
                    size
                FROM {self.schema}.training_ticks
                WHERE run_id = %s
                  AND instrument_id = %s
                  AND time >= %s::timestamp
                  AND time < %s::timestamp + interval '1 day'
                ORDER BY time
            """

            logger.info(
                f"Executing query for run_id={run_id}, instrument_id={instrument_id}, "
                f"date range: {start_date} to {end_date}"
            )

            cursor.execute(query, (run_id, instrument_id, start_date, end_date))

            # Fetch in chunks
            total_fetched = 0
            while True:
                rows = cursor.fetchmany(self.chunk_size)

                if not rows:
                    break

                df = pd.DataFrame(rows)
                total_fetched += len(df)

                logger.info(f"Fetched chunk: {len(df):,} rows (total: {total_fetched:,})")

                yield df

        except Exception as e:
            logger.error(f"Error streaming data: {e}", exc_info=True)
            raise
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def get_available_runs(self) -> pd.DataFrame:
        """Get available run_ids with metadata"""
        try:
            conn = psycopg2.connect(**self.db_config)

            query = f"""
                SELECT 
                    run_id,
                    COUNT(*) as tick_count,
                    MIN(time) as start_time,
                    MAX(time) as end_time,
                    COUNT(DISTINCT instrument_id) as instrument_count
                FROM {self.schema}.training_ticks
                GROUP BY run_id
                ORDER BY run_id
            """

            df = pd.read_sql_query(query, conn)
            conn.close()

            return df

        except Exception as e:
            logger.error(f"Error getting runs: {e}")
            return pd.DataFrame()