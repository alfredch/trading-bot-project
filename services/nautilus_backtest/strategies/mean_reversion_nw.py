"""
Mean Reversion Strategy with Nadaraya-Watson Bands
"""
import logging
from typing import Dict, Any

# TODO: Uncomment when Nautilus is fully configured
# from nautilus_trader.trading.strategy import Strategy
# from nautilus_trader.model.data import Bar
# from nautilus_trader.model.enums import OrderSide
# from nautilus_trader.model.orders import MarketOrder

from strategies.indicators.nadaraya_watson import NadarayaWatsonBands
from strategies.indicators.support_resistance import SupportResistanceLevels

logger = logging.getLogger(__name__)


class MeanReversionNWStrategy:
    """
    Mean-Reversion strategy using Nadaraya-Watson bands and S/R levels

    Entry Signals:
    - Long: Price touches lower NW band + near support level
    - Short: Price touches upper NW band + near resistance level

    Exit Signals:
    - Price reverts to NW center line
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize strategy

        Args:
            config: Strategy configuration
        """
        self.config = config

        # Indicators
        self.nw_bands = NadarayaWatsonBands(
            bandwidth=config.get('nw_bandwidth', 20),
            num_std=config.get('nw_std', 2.0)
        )

        self.sr_detector = SupportResistanceLevels(
            lookback=config.get('sr_lookback', 100),
            n_clusters=config.get('sr_clusters', 5)
        )

        # Position sizing
        self.position_size = config.get('position_size', 1)
        self.max_position = config.get('max_position', 2)

        # Data buffers
        self.prices = []
        self.highs = []
        self.lows = []

        logger.info(f"Strategy initialized with config: {config}")

    def on_bar(self, bar: Any):
        """
        Handle new bar data

        Args:
            bar: Bar data
        """
        # Update buffers
        self.prices.append(float(bar.close))
        self.highs.append(float(bar.high))
        self.lows.append(float(bar.low))

        # Need minimum data
        if len(self.prices) < 100:
            return

        # Calculate indicators
        self._update_indicators()

        # Generate signals
        self._check_signals(bar)

    def _update_indicators(self):
        """Update all indicators"""
        # Calculate NW bands
        import numpy as np

        x = np.arange(len(self.prices))
        y = np.array(self.prices)

        self.nw_center, self.upper_band, self.lower_band = \
            self.nw_bands.calculate(x, y)

        # Detect S/R levels
        self.support_levels, self.resistance_levels = \
            self.sr_detector.detect(self.highs[-100:], self.lows[-100:])

    def _check_signals(self, bar: Any):
        """Check for trading signals"""
        current_price = float(bar.close)
        current_nw = self.nw_center[-1]
        current_upper = self.upper_band[-1]
        current_lower = self.lower_band[-1]

        # Check entry conditions
        if self._check_long_entry(current_price, current_lower):
            logger.info(f"LONG signal at {current_price}")
            # TODO: Execute long order

        elif self._check_short_entry(current_price, current_upper):
            logger.info(f"SHORT signal at {current_price}")
            # TODO: Execute short order

        # Check exit conditions
        elif self._check_exit(current_price, current_nw):
            logger.info(f"EXIT signal at {current_price}")
            # TODO: Close position

    def _check_long_entry(self, price: float, lower_band: float) -> bool:
        """Check long entry conditions"""
        # Price at or below lower band
        if price > lower_band * 1.001:  # 0.1% tolerance
            return False

        # Near support level
        for support in self.support_levels:
            if abs(price - support) / price < 0.001:  # 0.1% proximity
                return True

        return False

    def _check_short_entry(self, price: float, upper_band: float) -> bool:
        """Check short entry conditions"""
        # Price at or above upper band
        if price < upper_band * 0.999:  # 0.1% tolerance
            return False

        # Near resistance level
        for resistance in self.resistance_levels:
            if abs(price - resistance) / price < 0.001:  # 0.1% proximity
                return True

        return False

    def _check_exit(self, price: float, nw_center: float) -> bool:
        """Check exit conditions"""
        # Price reverted to NW center
        return abs(price - nw_center) / price < 0.0005  # 0.05% proximity