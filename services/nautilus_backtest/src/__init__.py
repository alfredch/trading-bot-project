"""
Nautilus Backtest Service - Source Package
"""

# Core components
from .config import BacktestConfig
from .data_loader import ParquetDataLoader
from .backtest_engine import BacktestEngine

# Optional: Nautilus runner (may not be available during initial import)
try:
    from .nautilus_runner import NautilusBacktestRunner
except ImportError:
    NautilusBacktestRunner = None

__all__ = [
    'BacktestConfig',
    'ParquetDataLoader',
    'BacktestEngine',
    'NautilusBacktestRunner'
]