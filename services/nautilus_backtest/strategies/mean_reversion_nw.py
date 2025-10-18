"""
Mean Reversion Strategy with Nadaraya-Watson Bands - NAUTILUS VERSION
"""
import logging
from decimal import Decimal
from typing import Optional

import numpy as np
from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar, BarType
from nautilus_trader.model.enums import OrderSide, TimeInForce
from nautilus_trader.model.identifiers import InstrumentId
from nautilus_trader.model.orders import MarketOrder
from nautilus_trader.model.instruments import Instrument

# ✅ RICHTIG:
from strategies.indicators.nadaraya_watson import NadarayaWatsonBands
from strategies.indicators.support_resistance import SupportResistanceLevels

logger = logging.getLogger(__name__)


class MeanReversionNWStrategy(Strategy):
    """
    Mean-Reversion strategy using Nadaraya-Watson bands and S/R levels

    Entry Signals:
    - Long: Price touches lower NW band + near support level
    - Short: Price touches upper NW band + near resistance level

    Exit Signals:
    - Price reverts to NW center line
    """

    def __init__(self, config: Optional[dict] = None):
        """Initialize strategy with Nautilus base class"""
        super().__init__(config)

        # Strategy parameters
        self.instrument_id = InstrumentId.from_str(
            config.get('instrument_id', 'RUN10_INST643.SIM')
        )
        self.bar_type = BarType.from_str(
            config.get('bar_type', f'{self.instrument_id}-1-MINUTE-LAST-INTERNAL')
        )

        # Indicators
        self.nw_bands = NadarayaWatsonBands(
            bandwidth=config.get('nw_bandwidth', 20.0),
            num_std=config.get('nw_std', 2.0)
        )

        self.sr_detector = SupportResistanceLevels(
            lookback=config.get('sr_lookback', 100),
            n_clusters=config.get('sr_clusters', 5),
            tolerance=config.get('sr_tolerance', 0.02)
        )

        # Position sizing
        self.position_size = Decimal(str(config.get('position_size', 1)))
        self.max_position = config.get('max_position', 2)

        # Risk management
        self.stop_loss_pct = config.get('stop_loss_pct', 0.02)  # 2%
        self.take_profit_pct = config.get('take_profit_pct', 0.04)  # 4%

        # Data buffers
        self.prices = []
        self.highs = []
        self.lows = []
        self.bars_processed = 0

        # Indicator values
        self.nw_center = None
        self.upper_band = None
        self.lower_band = None
        self.support_levels = []
        self.resistance_levels = []

        # Warmup period
        self.warmup_period = config.get('warmup_period', 100)
        self.is_warmed_up = False

    def on_start(self):
        """Actions to be performed on strategy start"""
        self.instrument = self.cache.instrument(self.instrument_id)

        if self.instrument is None:
            self.log.error(f"Could not find instrument {self.instrument_id}")
            self.stop()
            return

        # Subscribe to bars
        self.subscribe_bars(self.bar_type)

        self.log.info(
            f"Strategy started for {self.instrument_id} "
            f"(warmup: {self.warmup_period} bars)"
        )

    def on_bar(self, bar: Bar):
        """
        Handle new bar data

        Args:
            bar: Bar data from Nautilus
        """
        self.bars_processed += 1

        # Update buffers
        close_price = float(bar.close)
        high_price = float(bar.high)
        low_price = float(bar.low)

        self.prices.append(close_price)
        self.highs.append(high_price)
        self.lows.append(low_price)

        # Keep only recent data (save memory)
        max_buffer = self.warmup_period * 2
        if len(self.prices) > max_buffer:
            self.prices = self.prices[-max_buffer:]
            self.highs = self.highs[-max_buffer:]
            self.lows = self.lows[-max_buffer:]

        # Check warmup
        if not self.is_warmed_up:
            if len(self.prices) >= self.warmup_period:
                self.is_warmed_up = True
                self.log.info(f"Strategy warmed up with {len(self.prices)} bars")
            else:
                return

        # Update indicators
        self._update_indicators()

        # Generate signals
        self._check_signals(bar)

        # Log progress
        if self.bars_processed % 1000 == 0:
            self.log.info(
                f"Processed {self.bars_processed:,} bars | "
                f"Price: {close_price:.2f} | "
                f"Position: {self.portfolio.net_position(self.instrument_id)}"
            )

    def _update_indicators(self):
        """Update all indicators"""
        try:
            # Calculate NW bands
            x = np.arange(len(self.prices))
            y = np.array(self.prices)

            nw_center, upper_band, lower_band = self.nw_bands.calculate(x, y)

            # Store current values (last element)
            self.nw_center = nw_center[-1]
            self.upper_band = upper_band[-1]
            self.lower_band = lower_band[-1]

            # Detect S/R levels (use recent data)
            lookback = min(self.sr_detector.lookback, len(self.highs))
            self.support_levels, self.resistance_levels = \
                self.sr_detector.detect(
                    self.highs[-lookback:],
                    self.lows[-lookback:]
                )

        except Exception as e:
            self.log.error(f"Error updating indicators: {e}")

    def _check_signals(self, bar: Bar):
        """Check for trading signals"""
        if self.nw_center is None:
            return

        current_price = float(bar.close)
        position = self.portfolio.net_position(self.instrument_id)

        # Check exit first
        if position != 0:
            if self._check_exit(current_price, position):
                self._close_position(current_price)
                return

        # Check entry only if no position
        if position == 0:
            if self._check_long_entry(current_price):
                self._enter_long(current_price)
            elif self._check_short_entry(current_price):
                self._enter_short(current_price)

    def _check_long_entry(self, price: float) -> bool:
        """Check long entry conditions"""
        # Price at or below lower band
        if price > self.lower_band * 1.001:  # 0.1% tolerance
            return False

        # Near support level
        for support in self.support_levels:
            proximity = abs(price - support) / price
            if proximity < 0.005:  # 0.5% proximity
                self.log.info(
                    f"LONG SIGNAL: Price {price:.2f} near support {support:.2f} "
                    f"(lower band: {self.lower_band:.2f})"
                )
                return True

        return False

    def _check_short_entry(self, price: float) -> bool:
        """Check short entry conditions"""
        # Price at or above upper band
        if price < self.upper_band * 0.999:  # 0.1% tolerance
            return False

        # Near resistance level
        for resistance in self.resistance_levels:
            proximity = abs(price - resistance) / price
            if proximity < 0.005:  # 0.5% proximity
                self.log.info(
                    f"SHORT SIGNAL: Price {price:.2f} near resistance {resistance:.2f} "
                    f"(upper band: {self.upper_band:.2f})"
                )
                return True

        return False

    def _check_exit(self, price: float, position: Decimal) -> bool:
        """
        Check exit conditions

        Args:
            price: Current price
            position: Current position (positive = long, negative = short)
        """
        # Mean reversion: exit when price returns to center
        distance_to_center = abs(price - self.nw_center) / price

        if distance_to_center < 0.001:  # 0.1% from center
            self.log.info(
                f"EXIT SIGNAL: Price {price:.2f} reverted to center {self.nw_center:.2f}"
            )
            return True

        # TODO: Add stop-loss and take-profit checks

        return False

    def _enter_long(self, price: float):
        """Enter long position"""
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.BUY,
            quantity=self.instrument.make_qty(self.position_size),
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self.log.info(f"LONG ORDER: {self.position_size} @ {price:.2f}")

    def _enter_short(self, price: float):
        """Enter short position"""
        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=OrderSide.SELL,
            quantity=self.instrument.make_qty(self.position_size),
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self.log.info(f"SHORT ORDER: {self.position_size} @ {price:.2f}")

    def _close_position(self, price: float):
        """Close current position"""
        position = self.portfolio.net_position(self.instrument_id)

        if position == 0:
            return

        # Determine side
        side = OrderSide.SELL if position > 0 else OrderSide.BUY

        order = self.order_factory.market(
            instrument_id=self.instrument_id,
            order_side=side,
            quantity=self.instrument.make_qty(abs(position)),
            time_in_force=TimeInForce.GTC,
        )

        self.submit_order(order)
        self.log.info(f"CLOSE POSITION: {position} @ {price:.2f}")

    def on_stop(self):
        """Actions to be performed on strategy stop"""
        # Close any open positions
        position = self.portfolio.net_position(self.instrument_id)
        if position != 0:
            self.log.warning(f"Closing position on stop: {position}")
            self._close_position(self.prices[-1] if self.prices else 0)

        self.log.info(f"Strategy stopped. Processed {self.bars_processed:,} bars")

    def on_reset(self):
        """Reset strategy state"""
        self.prices.clear()
        self.highs.clear()
        self.lows.clear()
        self.bars_processed = 0
        self.is_warmed_up = False

        self.log.info("Strategy reset")