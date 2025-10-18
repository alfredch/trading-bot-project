#!/usr/bin/env python3
"""
Nautilus Backtest Service - Main Entry Point
"""
import sys
import os
import logging

# Add src directory to Python path for relative imports
sys.path.insert(0, '/app/src')
sys.path.insert(0, '/app')

# Setup logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for nautilus backtest service"""
    try:
        logger.info("Nautilus Backtest Service starting...")

        # Import backtest engine (from src directory)
        from backtest_engine import BacktestEngine

        # Create and start engine
        engine = BacktestEngine()
        engine.run()

    except ImportError as e:
        logger.error(f"Import error: {e}", exc_info=True)
        logger.error("Python path:")
        for p in sys.path:
            logger.error(f"  - {p}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Backtest service interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()