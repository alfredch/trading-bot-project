"""
Configuration management for Data Pipeline
"""
import os
from typing import Dict


class Config:
    """Configuration class"""

    # PostgreSQL
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'trading_data')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'ts_admin')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')
    POSTGRES_SCHEMA = os.getenv('POSTGRES_SCHEMA', 'trading_schema')

    # Redis
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

    # Data Processing
    CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 1000000))

    # Paths
    PARQUET_PATH = os.getenv('PARQUET_PATH', '/data/parquet')
    LOGS_PATH = os.getenv('LOGS_PATH', '/app/logs')

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    def get_db_config(self) -> Dict[str, any]:
        """Get database configuration - OHNE schema Parameter"""
        return {
            'host': self.POSTGRES_HOST,
            'port': self.POSTGRES_PORT,
            'database': self.POSTGRES_DB,
            'user': self.POSTGRES_USER,
            'password': self.POSTGRES_PASSWORD
            # ❌ NICHT: 'schema': self.POSTGRES_SCHEMA
        }