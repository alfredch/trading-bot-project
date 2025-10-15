"""
Worker configuration management
"""
import os
from typing import Dict, Any


class WorkerConfig:
    """Worker configuration"""

    # Worker Identity
    WORKER_ID = os.getenv('WORKER_NAME', 'worker-unknown')
    WORKER_CONCURRENCY = int(os.getenv('WORKER_CONCURRENCY', 4))

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

    # PostgreSQL
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'trading_data')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'trading_user')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

    # Job Configuration
    JOB_TIMEOUT = int(os.getenv('JOB_TIMEOUT', 3600))
    JOB_MAX_RETRIES = int(os.getenv('JOB_MAX_RETRIES', 3))
    JOB_RETRY_DELAY = int(os.getenv('JOB_RETRY_DELAY', 60))

    # Worker Limits
    WORKER_MAX_JOBS = int(os.getenv('WORKER_MAX_JOBS_PER_WORKER', 100))
    WORKER_HEARTBEAT_INTERVAL = int(os.getenv('WORKER_HEARTBEAT_INTERVAL', 30))

    # Paths
    DATA_PATH = os.getenv('DATA_PATH', '/data/parquet')
    RESULTS_PATH = os.getenv('RESULTS_PATH', '/data/results')
    LOGS_PATH = os.getenv('LOGS_PATH', '/app/logs')

    # Processing
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000000))

    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """Get database configuration"""
        return {
            'host': cls.POSTGRES_HOST,
            'port': cls.POSTGRES_PORT,
            'database': cls.POSTGRES_DB,
            'user': cls.POSTGRES_USER,
            'password': cls.POSTGRES_PASSWORD
        }