"""
Trading Strategies Package
"""

# Try to import strategies (may fail if Nautilus not installed)
try:
    from .mean_reversion_nw import MeanReversionNWStrategy

    __all__ = ['MeanReversionNWStrategy']
except ImportError as e:
    # Nautilus not available yet
    __all__ = []
    import logging
    logging.getLogger(__name__).warning(f"Could not import strategies: {e}")