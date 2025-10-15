"""
Nautilus Backtest Engine
"""
import logging
import json
import time
import signal
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import redis

from src.config import BacktestConfig
from src.data_loader import ParquetDataLoader

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Engine for processing backtest jobs"""

    def __init__(self):
        """Initialize backtest engine"""
        self.config = BacktestConfig()
        self.running = True
        self.current_job_id = None

        # Redis connection
        self.redis = redis.Redis(
            host=self.config.REDIS_HOST,
            port=self.config.REDIS_PORT,
            decode_responses=True,
            socket_timeout=None
        )

        # Data loader
        self.data_loader = ParquetDataLoader(self.config.DATA_PATH)

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Backtest engine initialized")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal"""
        logger.info(f"Received shutdown signal {signum}")
        self.running = False

    def run(self):
        """Main engine loop"""
        logger.info("Backtest engine started. Waiting for jobs...")

        while self.running:
            try:
                # Wait for backtest jobs
                job_data = self.redis.brpop(['queue:backtest'], timeout=5)

                if not job_data:
                    continue

                _, job_id = job_data
                self.current_job_id = job_id

                logger.info(f"Processing backtest job: {job_id}")

                # Update status
                self._update_job_status(job_id, 'running', 0, 'Starting backtest...')

                # Process backtest
                start_time = time.time()
                success = self._process_backtest(job_id)
                duration = time.time() - start_time

                if success:
                    self._update_job_status(
                        job_id,
                        'completed',
                        100,
                        f'Backtest completed in {duration:.2f}s'
                    )
                    logger.info(f"Backtest {job_id} completed in {duration:.2f}s")

                self.current_job_id = None

            except redis.exceptions.TimeoutError:
                # Normal - kein Job verfügbar
                continue

            except Exception as e:
                logger.error(f"Error in backtest loop: {e}", exc_info=True)
                if self.current_job_id:
                    self._update_job_status(
                        self.current_job_id,
                        'failed',
                        0,
                        f'Error: {str(e)}'
                    )
                time.sleep(1)

        logger.info("Backtest engine shutting down")

    def _process_backtest(self, job_id: str) -> bool:
        """
        Process a backtest job

        Args:
            job_id: Job identifier

        Returns:
            True if successful
        """
        try:
            # Get job info
            job_info = self.redis.hgetall(f"job:{job_id}")

            if not job_info:
                logger.error(f"Job {job_id} not found")
                return False

            # Parse strategy config
            strategy_config = json.loads(job_info.get('strategy', '{}'))

            strategy_name = strategy_config.get('name')
            run_id = strategy_config.get('run_id')
            instrument_id = strategy_config.get('instrument_id')
            start_date = strategy_config.get('start_date')
            end_date = strategy_config.get('end_date')
            config = strategy_config.get('config', {})

            # Build instrument identifier (same format as migration)
            instrument = f"RUN{run_id}_INST{instrument_id}"

            logger.info(
                f"Running backtest: {strategy_name} on {instrument} "
                f"({start_date} to {end_date})"
            )

            # Update progress
            self._update_job_status(job_id, 'running', 10, 'Loading data...')

            # Load data
            df = self.data_loader.load_instrument_data(
                instrument,
                start_date,
                end_date
            )

            if df.empty:
                raise ValueError(f"No data found for {instrument}")

            logger.info(f"Loaded {len(df):,} ticks for backtest")

            self._update_job_status(job_id, 'running', 30, 'Preparing backtest...')

            # Run backtest
            results = self._run_nautilus_backtest(
                strategy_name=strategy_name,
                instrument=instrument,
                data=df,
                config=config,
                job_id=job_id
            )

            # Add metadata
            results.update({
                'job_id': job_id,
                'strategy': strategy_name,
                'instrument': instrument,
                'run_id': run_id,
                'instrument_id': instrument_id,
                'start_date': start_date,
                'end_date': end_date
            })

            self._update_job_status(job_id, 'running', 90, 'Saving results...')

            # Save results
            self._save_results(job_id, results)

            return True

        except Exception as e:
            logger.error(f"Backtest processing error: {e}", exc_info=True)
            return False

    def _run_nautilus_backtest(
        self,
        strategy_name: str,
        instrument: str,
        data: Any,
        config: Dict[str, Any],
        job_id: str
    ) -> Dict[str, Any]:
        """
        Run Nautilus backtest

        Args:
            strategy_name: Name of strategy
            instrument: Instrument identifier
            data: Market data
            config: Strategy configuration
            job_id: Job ID for progress updates

        Returns:
            Backtest results
        """
        try:
            # TODO: Implement actual Nautilus backtest
            # For now, mock implementation

            logger.info(f"Running backtest with {len(data):,} ticks")

            # Simulate backtest phases
            phases = [
                (40, 'Initializing strategy...'),
                (50, 'Processing data...'),
                (60, 'Executing trades...'),
                (70, 'Calculating PnL...'),
                (80, 'Generating metrics...')
            ]

            for progress, message in phases:
                self._update_job_status(job_id, 'running', progress, message)
                time.sleep(1)  # Simulate work

            # Mock results
            results = {
                'total_trades': 42,
                'winning_trades': 28,
                'losing_trades': 14,
                'win_rate': 66.67,
                'total_pnl': 12500.00,
                'gross_profit': 15000.00,
                'gross_loss': -2500.00,
                'avg_trade': 297.62,
                'avg_win': 535.71,
                'avg_loss': -178.57,
                'profit_factor': 6.00,
                'max_drawdown': -2100.00,
                'max_drawdown_pct': -2.10,
                'sharpe_ratio': 1.85,
                'ticks_processed': len(data),
                'execution_time': time.time(),
                'config': config
            }

            return results

        except ImportError:
            logger.warning("Nautilus Trader not fully configured, using mock backtest")

            # Basic mock results
            return {
                'status': 'mock',
                'message': 'Mock backtest - Nautilus not configured',
                'ticks_processed': len(data),
                'config': config
            }

    def _save_results(self, job_id: str, results: Dict[str, Any]):
        """Save backtest results"""
        try:
            # Save to file
            results_path = Path(self.config.RESULTS_PATH)
            results_path.mkdir(parents=True, exist_ok=True)

            results_file = results_path / f"{job_id}.json"

            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)

            # Save to Redis
            self.redis.hset(
                f"job:{job_id}",
                'results',
                json.dumps(results)
            )

            logger.info(f"Results saved to {results_file}")

        except Exception as e:
            logger.error(f"Error saving results: {e}")

    def _update_job_status(self, job_id: str, status: str, progress: int, message: str):
        """Update job status in Redis"""
        try:
            self.redis.hset(f"job:{job_id}", mapping={
                'status': status,
                'progress': progress,
                'message': message,
                'updated_at': datetime.now().isoformat()
            })

            self.redis.publish(
                f"jobs:progress:{job_id}",
                json.dumps({
                    'job_id': job_id,
                    'status': status,
                    'progress': progress,
                    'message': message
                })
            )
        except Exception as e:
            logger.error(f"Error updating job status: {e}")