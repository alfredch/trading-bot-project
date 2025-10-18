"""
Nautilus Backtest Runner - Runs actual backtests with Nautilus Trader
COMPLETE FIXED VERSION
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

import pandas as pd
from nautilus_trader.backtest.node import BacktestNode
from nautilus_trader.model.identifiers import Venue, TraderId
from nautilus_trader.model.currencies import USD
from nautilus_trader.model.enums import AccountType, OmsType
from nautilus_trader.model.objects import Money

logger = logging.getLogger(__name__)


class NautilusBacktestRunner:
    """
    Run backtests using Nautilus Trader
    """

    def __init__(self):
        """Initialize backtest runner"""
        self.venue = Venue("SIM")
        self.trader_id = TraderId("BACKTESTER-001")

    def run_backtest(
        self,
        strategy_class,
        strategy_config: Dict[str, Any],
        data: pd.DataFrame,
        instrument_id_str: str,
        initial_capital: float = 100_000.0
    ) -> Dict[str, Any]:
        """
        Run a backtest with Nautilus Trader

        Args:
            strategy_class: Strategy class to instantiate
            strategy_config: Strategy configuration
            data: Market data (DataFrame with tick data)
            instrument_id_str: Instrument identifier
            initial_capital: Initial capital in USD

        Returns:
            Dictionary with backtest results
        """
        try:
            logger.info(f"Starting Nautilus backtest with {len(data):,} ticks")

            # Create instrument
            instrument = self._create_instrument(instrument_id_str)

            # Prepare data
            ticks = self._prepare_data(data, instrument)

            if not ticks:
                raise ValueError("No ticks prepared for backtest")

            logger.info(f"Prepared {len(ticks):,} ticks for backtest")

            # Create backtest node
            node = BacktestNode()

            # Add venue config
            node.add_venue(
                venue=self.venue,
                oms_type=OmsType.NETTING,
                account_type=AccountType.CASH,
                base_currency=USD,
                starting_balances=[Money(initial_capital, USD)]
            )

            # Add instrument
            node.add_instrument(instrument)

            # Add data
            node.add_data(ticks)

            # Add strategy
            strategy_config_with_id = strategy_config.copy()
            strategy_config_with_id['instrument_id'] = f"{instrument.id.symbol}.{self.venue}"

            node.add_strategy(strategy_class, strategy_config_with_id)

            # Run backtest
            logger.info("Running Nautilus backtest...")
            result = node.run()

            # Extract results
            results = self._extract_results(node, len(data))

            logger.info("Nautilus backtest completed successfully")

            return results

        except Exception as e:
            logger.error(f"Backtest failed: {e}", exc_info=True)
            raise

    def _create_instrument(self, instrument_id_str: str):
        """
        Create a Nautilus instrument

        Args:
            instrument_id_str: Instrument identifier (e.g., 'RUN10_INST643')

        Returns:
            Nautilus Instrument
        """
        from nautilus_trader.model.instruments import Equity
        from nautilus_trader.model.identifiers import Symbol, InstrumentId
        from nautilus_trader.model.objects import Price, Quantity
        from nautilus_trader.model.currencies import USD

        # Shorten symbol to fit Nautilus constraints (remove underscores, max 10 chars)
        short_symbol = instrument_id_str.replace('_', '')[:10]  # "RUN10INST643" -> "RUN10INST6"

        symbol = Symbol(short_symbol)
        instrument_id = InstrumentId(symbol=symbol, venue=self.venue)

        # Create Equity instrument with correct parameters for Nautilus 1.220.0
        instrument = Equity(
            instrument_id=instrument_id,
            raw_symbol=Symbol(short_symbol),
            currency=USD,
            price_precision=5,
            price_increment=Price.from_str("0.00001"),
            lot_size=Quantity.from_int(1),
            isin=None,
            ts_event=0,
            ts_init=0,
        )

        logger.info(f"Created instrument: {instrument.id} from {instrument_id_str}")

        return instrument

    def _prepare_data(self, df: pd.DataFrame, instrument):
        """
        Convert DataFrame to Nautilus ticks

        Args:
            df: DataFrame with columns: ts_event, price, size (trade ticks)
                or: ts_event, bid_price, ask_price, bid_size, ask_size (quote ticks)
            instrument: Nautilus instrument

        Returns:
            List of QuoteTick objects
        """
        try:
            logger.info(f"Preparing {len(df)} ticks. Columns: {df.columns.tolist()}")

            # Check if we have quote data or trade data
            if 'bid_price' not in df.columns and 'price' in df.columns:
                logger.info("Converting trade ticks to quote ticks with synthetic bid/ask")

                # Create synthetic bid/ask with small spread (0.02% = 2 basis points)
                spread_pct = 0.0002
                spread = df['price'] * spread_pct

                df = df.copy()
                df['bid_price'] = df['price'] - spread / 2
                df['ask_price'] = df['price'] + spread / 2
                df['bid_size'] = df['size']
                df['ask_size'] = df['size']

                logger.info(f"Created bid/ask from price. Sample: bid={df['bid_price'].iloc[0]:.5f}, ask={df['ask_price'].iloc[0]:.5f}")

            # Ensure required columns exist
            required_cols = ['ts_event', 'bid_price', 'ask_price', 'bid_size', 'ask_size']
            missing_cols = [col for col in required_cols if col not in df.columns]

            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}. Available: {df.columns.tolist()}")

            # Prepare DataFrame for wrangler
            df_prepared = df.copy()

            # Convert timestamp to datetime with UTC timezone
            logger.info("Converting timestamps to UTC datetime...")
            if not pd.api.types.is_datetime64_any_dtype(df_prepared['ts_event']):
                df_prepared['ts_event'] = pd.to_datetime(df_prepared['ts_event'], unit='ns', utc=True)
            else:
                # Ensure UTC timezone
                if df_prepared['ts_event'].dt.tz is None:
                    df_prepared['ts_event'] = df_prepared['ts_event'].dt.tz_localize('UTC')
                else:
                    df_prepared['ts_event'] = df_prepared['ts_event'].dt.tz_convert('UTC')

            # Rename columns to match Nautilus expectations
            df_prepared = df_prepared.rename(columns={
                'ts_event': 'timestamp',
                'bid_price': 'bid',
                'ask_price': 'ask',
                'bid_size': 'bid_size',
                'ask_size': 'ask_size'
            })

            # CRITICAL: Set timestamp as index (Nautilus requirement)
            logger.info("Setting timestamp as index...")
            df_prepared = df_prepared.set_index('timestamp')

            # Ensure all required columns are numeric
            logger.info("Converting columns to numeric types...")
            df_prepared['bid'] = pd.to_numeric(df_prepared['bid'], errors='coerce')
            df_prepared['ask'] = pd.to_numeric(df_prepared['ask'], errors='coerce')
            df_prepared['bid_size'] = pd.to_numeric(df_prepared['bid_size'], errors='coerce')
            df_prepared['ask_size'] = pd.to_numeric(df_prepared['ask_size'], errors='coerce')

            # Drop any rows with NaN values
            initial_len = len(df_prepared)
            df_prepared = df_prepared.dropna()
            if len(df_prepared) < initial_len:
                logger.warning(f"Dropped {initial_len - len(df_prepared)} rows with NaN values")

            # Validate data
            if df_prepared.empty:
                raise ValueError("DataFrame is empty after preparation")

            if not isinstance(df_prepared.index, pd.DatetimeIndex):
                raise ValueError(f"Index must be DatetimeIndex, got {type(df_prepared.index)}")

            if df_prepared.index.tz is None:
                raise ValueError("Index must have timezone information (UTC)")

            logger.info(f"Data prepared: {len(df_prepared)} rows, index type: {type(df_prepared.index)}, timezone: {df_prepared.index.tz}")
            logger.info(f"Sample data:\n{df_prepared.head(2)}")

            # Use QuoteTickDataWrangler to convert to Nautilus ticks
            from nautilus_trader.persistence.wranglers import QuoteTickDataWrangler

            logger.info("Processing with QuoteTickDataWrangler...")
            wrangler = QuoteTickDataWrangler(instrument)
            ticks = wrangler.process(df_prepared)

            logger.info(f"Successfully prepared {len(ticks)} Nautilus ticks")

            return ticks

        except Exception as e:
            logger.error(f"Error preparing data: {e}", exc_info=True)
            raise

    def _extract_results(self, node: BacktestNode, ticks_count: int) -> Dict[str, Any]:
        """
        Extract backtest results from Nautilus node

        Args:
            node: Backtest node with results
            ticks_count: Number of ticks processed

        Returns:
            Dictionary with results
        """
        try:
            # Get account
            accounts = list(node.portfolio.accounts.values())
            account = accounts[0] if accounts else None

            if not account:
                logger.warning("No account found in backtest results")
                return {
                    'status': 'completed',
                    'ticks_processed': ticks_count,
                    'message': 'No account data available'
                }

            # Get orders and fills
            orders = node.trader.generate_order_fills_report()
            positions = node.trader.generate_positions_report()

            # Calculate metrics
            total_trades = len(orders)
            winning_trades = len([o for o in orders if float(o.get('realized_pnl', 0)) > 0])
            losing_trades = len([o for o in orders if float(o.get('realized_pnl', 0)) < 0])

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

            # PnL calculations
            realized_pnls = [float(o.get('realized_pnl', 0)) for o in orders]
            total_pnl = sum(realized_pnls)

            gross_profit = sum([pnl for pnl in realized_pnls if pnl > 0])
            gross_loss = sum([pnl for pnl in realized_pnls if pnl < 0])

            avg_trade = total_pnl / total_trades if total_trades > 0 else 0
            avg_win = gross_profit / winning_trades if winning_trades > 0 else 0
            avg_loss = gross_loss / losing_trades if losing_trades > 0 else 0

            profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0

            # Account metrics
            balance = float(account.balance_total(USD))
            equity = float(account.balance_total(USD))  # For cash account

            results = {
                'status': 'completed',
                'ticks_processed': ticks_count,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'win_rate': round(win_rate, 2),
                'total_pnl': round(total_pnl, 2),
                'gross_profit': round(gross_profit, 2),
                'gross_loss': round(gross_loss, 2),
                'avg_trade': round(avg_trade, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'profit_factor': round(profit_factor, 2),
                'final_balance': round(balance, 2),
                'final_equity': round(equity, 2),
                'return_pct': round((equity / 100000.0 - 1) * 100, 2),
                'orders': orders,
                'positions': positions
            }

            logger.info(f"Results extracted: {total_trades} trades, PnL: {total_pnl:.2f}")

            return results

        except Exception as e:
            logger.error(f"Error extracting results: {e}", exc_info=True)
            return {
                'status': 'error',
                'message': str(e),
                'ticks_processed': ticks_count
            }