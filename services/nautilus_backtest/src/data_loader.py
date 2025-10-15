"""
Data loader for Nautilus backtests - SIMPLE VERSION
"""
import logging
from pathlib import Path
from typing import List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ParquetDataLoader:
    """Load tick data from Parquet files for backtesting"""

    def __init__(self, data_path: str):
        """
        Initialize data loader

        Args:
            data_path: Path to parquet data directory
        """
        self.data_path = Path(data_path)

    def load_instrument_data(
        self,
        instrument: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load data for an instrument

        Args:
            instrument: Instrument identifier (e.g., 'RUN10_INST643')
            start_date: Start date (ISO format)
            end_date: End date (ISO format)

        Returns:
            DataFrame with tick data
        """
        instrument_path = self.data_path / instrument

        if not instrument_path.exists():
            raise FileNotFoundError(f"Data path not found: {instrument_path}")

        logger.info(f"Loading data from {instrument_path}")

        try:
            # Build list of date directories to read
            if start_date and end_date:
                # Filter directories by date
                date_dirs = []
                for date_dir in sorted(instrument_path.glob('date=*')):
                    date_str = date_dir.name.split('=')[1]
                    if start_date <= date_str <= end_date:
                        date_dirs.append(date_dir)

                if not date_dirs:
                    logger.warning(f"No data found for date range {start_date} to {end_date}")
                    return pd.DataFrame()

                logger.info(f"Loading {len(date_dirs)} date partitions")

            else:
                # Load all dates
                date_dirs = list(instrument_path.glob('date=*'))
                logger.info(f"Loading all {len(date_dirs)} date partitions")

            # Read parquet files from selected directories
            dfs = []
            total_files = 0

            for date_dir in date_dirs:
                parquet_files = list(date_dir.glob('*.parquet'))
                total_files += len(parquet_files)

                for parquet_file in parquet_files:
                    df_chunk = pd.read_parquet(parquet_file)
                    dfs.append(df_chunk)

            if not dfs:
                raise FileNotFoundError(f"No parquet files found in {instrument_path}")

            logger.info(f"Read {total_files} parquet files")

            # Combine all chunks
            df = pd.concat(dfs, ignore_index=True)

            logger.info(f"Loaded {len(df):,} total rows")

            # Sort by timestamp
            df = df.sort_values('ts_event').reset_index(drop=True)

            logger.info(f"Returning {len(df):,} rows for {instrument}")

            return df

        except Exception as e:
            logger.error(f"Error loading data: {e}", exc_info=True)
            raise

    def get_available_dates(self, instrument: str) -> List[str]:
        """Get list of available dates for an instrument"""
        instrument_path = self.data_path / instrument

        if not instrument_path.exists():
            return []

        dates = []
        for date_dir in sorted(instrument_path.glob('date=*')):
            date = date_dir.name.split('=')[1]
            dates.append(date)

        return dates