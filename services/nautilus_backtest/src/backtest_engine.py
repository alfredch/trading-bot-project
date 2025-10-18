"""
Nautilus Backtest Engine - WITH REAL NAUTILUS INTEGRATION
"""
import logging
import json
import time
import signal
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path

import redis

# ✅ Korrekte Imports (ohne 'services.nautilus_backtest.src')
from config import BacktestConfig
from data_loader import ParquetDataLoader
from nautilus_runner import NautilusBacktestRunner

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Engine for processing backtest jobs with real Nautilus Trader"""

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

        # Nautilus runner
        self.nautilus_runner = NautilusBacktestRunner()

        # Signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        logger.info("Backtest engine initialized with Nautilus Trader")

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
                # Normal - no job available
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

            # Build instrument identifier
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

            # Run REAL Nautilus backtest
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
                'end_date': end_date,
                'config': config
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
        Run REAL Nautilus backtest

        Args:
            strategy_name: Name of strategy
            instrument: Instrument identifier
            data: Market data (DataFrame)
            config: Strategy configuration
            job_id: Job ID for progress updates

        Returns:
            Backtest results
        """
        try:
            self._update_job_status(job_id, 'running', 40, 'Initializing Nautilus...')

            # Import strategy class
            from strategies.mean_reversion_nw import MeanReversionNWStrategy

            strategy_map = {
                'mean_reversion_nw': MeanReversionNWStrategy,
                'MeanReversionNWStrategy': MeanReversionNWStrategy
            }

            strategy_class = strategy_map.get(strategy_name)

            if not strategy_class:
                raise ValueError(f"Unknown strategy: {strategy_name}")

            logger.info(f"Using strategy: {strategy_class.__name__}")

            self._update_job_status(job_id, 'running', 50, 'Loading data into Nautilus...')

            # Run backtest with Nautilus
            results = self.nautilus_runner.run_backtest(
                strategy_class=strategy_class,
                strategy_config=config,
                data=data,
                instrument_id_str=instrument,
                initial_capital=config.get('initial_capital', 100_000.0)
            )

            self._update_job_status(job_id, 'running', 80, 'Backtest completed, processing results...')

            logger.info(f"Nautilus backtest completed: {results.get('total_trades', 0)} trades")

            return results

        except ImportError as e:
            logger.error(f"Import error - Nautilus not available: {e}", exc_info=True)
            return self._fallback_mock_backtest(data, config)

        except Exception as e:
            logger.error(f"Nautilus backtest error: {e}", exc_info=True)
            raise

    def _fallback_mock_backtest(self, data: Any, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback mock backtest if Nautilus fails

        Args:
            data: Market data
            config: Strategy config

        Returns:
            Mock results
        """
        logger.warning("Using MOCK backtest - Nautilus integration failed")

        return {
            'status': 'mock',
            'message': 'Mock backtest - Nautilus integration error',
            'ticks_processed': len(data),
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'total_pnl': 0.0,
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
                json.dump(results, f, indent=2, default=str)

            # Save to Redis
            self.redis.hset(
                f"job:{job_id}",
                'results',
                json.dumps(results, default=str)
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