#!/usr/bin/env python3
"""
Validate Parquet files
"""
import sys
from pathlib import Path
import pandas as pd
import pyarrow.parquet as pq


def validate_parquet(instrument_path: str):
    """Validate parquet data"""

    path = Path(instrument_path)

    if not path.exists():
        print(f"❌ Path not found: {path}")
        return False

    try:
        # Read parquet dataset
        dataset = pq.ParquetDataset(path)
        table = dataset.read()
        df = table.to_pandas()

        # Convert date from categorical to proper type
        if df['date'].dtype.name == 'category':
            df['date'] = pd.to_datetime(df['date'].astype(str))

        print('═' * 50)
        print('✅ PARQUET VALIDATION SUCCESSFUL!')
        print('═' * 50)
        print(f'Path: {path}')
        print(f'Total rows: {len(df):,}')
        print(f'Columns: {list(df.columns)}')
        print(f'Date range: {df.date.min()} to {df.date.max()}')
        print(f'Price range: ${df.price.min():.2f} to ${df.price.max():.2f}')
        print(f'Size range: {df["size"].min():.2f} to {df["size"].max():.2f}')
        print(f'Memory usage: {df.memory_usage(deep=True).sum() / 1024 ** 2:.2f} MB')

        # File info
        files = list(path.rglob('*.parquet'))
        total_size = sum(f.stat().st_size for f in files)
        print(f'Files: {len(files)}')
        print(f'Disk size: {total_size / 1024 ** 2:.2f} MB')
        print(f'Compression ratio: {df.memory_usage(deep=True).sum() / total_size:.2f}x')

        print()
        print('─' * 50)
        print('First 5 rows:')
        print('─' * 50)
        print(df.head(5).to_string())

        print()
        print('─' * 50)
        print('Last 5 rows:')
        print('─' * 50)
        print(df.tail(5).to_string())

        print()
        print('─' * 50)
        print('Data Types:')
        print('─' * 50)
        print(df.dtypes)

        print()
        print('─' * 50)
        print('Summary Statistics:')
        print('─' * 50)
        print(df[['price', 'size']].describe())

        print()
        print('─' * 50)
        print('Timestamp Info:')
        print('─' * 50)
        # Convert nanosecond timestamps to datetime for display
        df['time'] = pd.to_datetime(df['ts_event'], unit='ns')
        print(f'First timestamp: {df["time"].iloc[0]}')
        print(f'Last timestamp: {df["time"].iloc[-1]}')
        print(f'Duration: {df["time"].iloc[-1] - df["time"].iloc[0]}')
        print(f'Ticks per second: {len(df) / (df["time"].iloc[-1] - df["time"].iloc[0]).total_seconds():.2f}')

        return True

    except Exception as e:
        print(f"❌ Error reading parquet: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        instrument_path = sys.argv[1]
    else:
        instrument_path = 'data/parquet/RUN10_INST643'

    success = validate_parquet(instrument_path)
    sys.exit(0 if success else 1)