"""
Nautilus Backtest Configuration
"""
import os
from typing import Dict, Any


class BacktestConfig:
    """Backtest configuration"""

    # Service
    SERVICE_NAME = os.getenv('SERVICE_NAME', 'nautilus_backtest')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

    # Paths
    DATA_PATH = os.getenv('DATA_PATH', '/data/parquet')
    RESULTS_PATH = os.getenv('RESULTS_PATH', '/data/results')
    LOGS_PATH = os.getenv('LOGS_PATH', '/app/logs')

    # Backtest Settings
    BACKTEST_TIMEOUT = int(os.getenv('BACKTEST_TIMEOUT', 3600))

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def get_data_path(cls, instrument: str) -> str:
        """Get data path for instrument"""
        return os.path.join(cls.DATA_PATH, instrument)

    @classmethod
    def get_results_path(cls, job_id: str) -> str:
        """Get results path for job"""
        return os.path.join(cls.RESULTS_PATH, f"{job_id}.json")