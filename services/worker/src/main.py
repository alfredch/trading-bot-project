#!/usr/bin/env python3
"""
Worker Service - Main Entry Point
"""
import sys
import os
import logging

# Add app directory to Python path
sys.path.insert(0, '/app')

# Setup basic logging immediately
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for worker"""
    try:
        logger.info("Worker service starting...")

        # Import worker class
        from src.worker import EnhancedWorker

        # Create and start worker
        worker = EnhancedWorker()
        worker.process_jobs()

    except ImportError as e:
        logger.error(f"Import error: {e}", exc_info=True)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()