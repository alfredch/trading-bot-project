"""
Backtest Results Analyzer
"""
import logging
from typing import Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


class ResultsAnalyzer:
    """Analyze and format backtest results"""

    @staticmethod
    def calculate_metrics(trades: list, initial_capital: float = 100000) -> Dict[str, Any]:
        """
        Calculate comprehensive trading metrics

        Args:
            trades: List of trade records
            initial_capital: Starting capital

        Returns:
            Dictionary of calculated metrics
        """
        if not trades:
            return {
                'total_trades': 0,
                'status': 'no_trades'
            }

        # Basic stats
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
        losing_trades = [t for t in trades if t.get('pnl', 0) < 0]

        # PnL calculations
        pnl_list = [t.get('pnl', 0) for t in trades]
        total_pnl = sum(pnl_list)
        gross_profit = sum([t.get('pnl', 0) for t in winning_trades])
        gross_loss = sum([t.get('pnl', 0) for t in losing_trades])

        # Win rate
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0

        # Average trade
        avg_trade = total_pnl / total_trades if total_trades > 0 else 0
        avg_win = gross_profit / len(winning_trades) if winning_trades else 0
        avg_loss = gross_loss / len(losing_trades) if losing_trades else 0

        # Profit factor
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else 0

        # Calculate drawdown
        equity_curve = np.cumsum([initial_capital] + pnl_list)
        running_max = np.maximum.accumulate(equity_curve)
        drawdown = equity_curve - running_max
        max_drawdown = np.min(drawdown)
        max_drawdown_pct = (max_drawdown / running_max[np.argmin(drawdown)]) * 100 if running_max[np.argmin(
            drawdown)] > 0 else 0

        # Sharpe ratio (simplified)
        if len(pnl_list) > 1:
            returns = np.array(pnl_list) / initial_capital
            sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe_ratio = 0

        # Return on capital
        final_capital = initial_capital + total_pnl
        roi = (total_pnl / initial_capital) * 100

        return {
            'total_trades': total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': round(win_rate, 2),
            'total_pnl': round(total_pnl, 2),
            'gross_profit': round(gross_profit, 2),
            'gross_loss': round(gross_loss, 2),
            'avg_trade': round(avg_trade, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'profit_factor': round(profit_factor, 2),
            'max_drawdown': round(max_drawdown, 2),
            'max_drawdown_pct': round(max_drawdown_pct, 2),
            'sharpe_ratio': round(sharpe_ratio, 2),
            'initial_capital': initial_capital,
            'final_capital': round(final_capital, 2),
            'roi': round(roi, 2)
        }

    @staticmethod
    def format_results(metrics: Dict[str, Any], job_info: Dict[str, Any]) -> Dict[str, Any]:
        """Format results for storage and display"""
        return {
            'job_id': job_info.get('job_id'),
            'timestamp': job_info.get('timestamp'),
            'strategy': job_info.get('strategy'),
            'instrument': job_info.get('instrument'),
            'period': {
                'start': job_info.get('start_date'),
                'end': job_info.get('end_date')
            },
            'performance': metrics,
            'config': job_info.get('config', {})
        }