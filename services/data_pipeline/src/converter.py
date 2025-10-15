"""
Convert tick data to Nautilus Trader Parquet format
"""
import logging
from pathlib import Path
from typing import Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


class ParquetConverter:
    """
    Convert and write tick data to Nautilus-compatible Parquet format
    """

    def __init__(self, output_dir: Path):
        """
        Initialize converter

        Args:
            output_dir: Output directory for Parquet files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_nautilus_schema(self, df: pd.DataFrame,
                          run_id: int,
                          instrument_id: int) -> pd.DataFrame:
        """
        Convert DataFrame to Nautilus schema

        Args:
            df: Input DataFrame from TimescaleDB
            run_id: Run ID
            instrument_id: Instrument ID

        Returns:
            DataFrame with Nautilus schema
        """
        df_nautilus = df.copy()

        # Convert timestamp to nanoseconds (Nautilus requirement)
        df_nautilus['ts_event'] = pd.to_datetime(df_nautilus['time']).astype('int64')
        df_nautilus['ts_init'] = df_nautilus['ts_event']

        # Instrument identifier (format: RUN{run_id}_INST{instrument_id})
        instrument_str = f"RUN{run_id}_INST{instrument_id}"
        df_nautilus['instrument_id'] = instrument_str

        # Rename columns to Nautilus conventions
        df_nautilus['price'] = df_nautilus['price'].astype('float64')
        df_nautilus['size'] = df_nautilus['size'].astype('float64')

        # Add date partition column for efficient querying
        df_nautilus['date'] = pd.to_datetime(df_nautilus['time']).dt.date

        # Select final columns
        columns = [
            'instrument_id',
            'ts_event',
            'ts_init',
            'price',
            'size',
            'date'
        ]

        return df_nautilus[columns]

    def write_parquet_partitioned(self,
                                  df: pd.DataFrame,
                                  run_id: int,
                                  instrument_id: int,
                                  chunk_idx: int):
        """
        Write DataFrame to partitioned Parquet files

        Args:
            df: DataFrame to write
            run_id: Run ID
            instrument_id: Instrument ID
            chunk_idx: Chunk index for logging
        """
        try:
            # Create directory structure: RUN{run_id}/INST{instrument_id}/
            instrument_str = f"RUN{run_id}_INST{instrument_id}"
            instrument_dir = self.output_dir / instrument_str
            instrument_dir.mkdir(parents=True, exist_ok=True)

            # Convert to PyArrow Table
            table = pa.Table.from_pandas(df)

            # Write with partitioning by date
            pq.write_to_dataset(
                table,
                root_path=str(instrument_dir),
                partition_cols=['date'],
                compression='snappy',
                use_dictionary=True,
                write_statistics=True,
                existing_data_behavior='overwrite_or_ignore'
            )

            logger.info(
                f"Wrote chunk {chunk_idx} for RUN{run_id}/INST{instrument_id}: "
                f"{len(df):,} rows"
            )

        except Exception as e:
            logger.error(f"Error writing Parquet: {e}", exc_info=True)
            raise