"""
Base processor class
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict
import redis

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """Base class for job processors"""

    def __init__(self, redis_client: redis.Redis, worker_id: str):
        self.redis = redis_client
        self.worker_id = worker_id

    @abstractmethod
    def process(self, job_id: str, *args, **kwargs) -> bool:
        """Process a job"""
        pass

    def update_progress(self, job_id: str, progress: int, message: str):
        """Update job progress"""
        try:
            self.redis.hset(f"job:{job_id}", mapping={
                'progress': progress,
                'message': message
            })
        except Exception as e:
            logger.error(f"Error updating progress: {e}")