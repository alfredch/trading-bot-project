"""
Generate HTML/PDF reports from backtest results
"""
import logging
from typing import Dict, Any
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate backtest reports"""

    @staticmethod
    def generate_html_report(results: Dict[str, Any], output_path: Path) -> str:
        """
        Generate HTML report

        Args:
            results: Backtest results
            output_path: Output file path

        Returns:
            Path to generated report
        """
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Backtest Report - {results.get('strategy', 'Unknown')}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #555;
            margin-top: 30px;
        }}
        .metric {{
            display: inline-block;
            margin: 10px 20px 10px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            min-width: 200px;
        }}
        .metric-label {{
            font-weight: bold;
            color: #666;
            font-size: 14px;
        }}
        .metric-value {{
            font-size: 24px;
            color: #333;
            margin-top: 5px;
        }}
        .positive {{
            color: #4CAF50;
        }}
        .negative {{
            color: #f44336;
        }}
        .info-section {{
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Backtest Report</h1>

        <div class="info-section">
            <h2>Strategy Information</h2>
            <p><strong>Strategy:</strong> {results.get('strategy', 'N/A')}</p>
            <p><strong>Instrument:</strong> {results.get('instrument', 'N/A')}</p>
            <p><strong>Period:</strong> {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')}</p>
            <p><strong>Job ID:</strong> {results.get('job_id', 'N/A')}</p>
        </div>

        <h2>Performance Summary</h2>
        <div>
            <div class="metric">
                <div class="metric-label">Total PnL</div>
                <div class="metric-value {'positive' if results.get('total_pnl', 0) > 0 else 'negative'}">
                    ${results.get('total_pnl', 0):,.2f}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Win Rate</div>
                <div class="metric-value">
                    {results.get('win_rate', 0):.1f}%
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Sharpe Ratio</div>
                <div class="metric-value">
                    {results.get('sharpe_ratio', 0):.2f}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Max Drawdown</div>
                <div class="metric-value negative">
                    ${results.get('max_drawdown', 0):,.2f}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Total Trades</div>
                <div class="metric-value">
                    {results.get('total_trades', 0)}
                </div>
            </div>

            <div class="metric">
                <div class="metric-label">Profit Factor</div>
                <div class="metric-value">
                    {results.get('profit_factor', 0):.2f}
                </div>
            </div>
        </div>

        <h2>Detailed Statistics</h2>
        <table>
            <tr>
                <th>Metric</th>
                <th>Value</th>
            </tr>
            <tr>
                <td>Total Trades</td>
                <td>{results.get('total_trades', 0)}</td>
            </tr>
            <tr>
                <td>Winning Trades</td>
                <td>{results.get('winning_trades', 0)}</td>
            </tr>
            <tr>
                <td>Losing Trades</td>
                <td>{results.get('losing_trades', 0)}</td>
            </tr>
            <tr>
                <td>Average Trade</td>
                <td>${results.get('avg_trade', 0):,.2f}</td>
            </tr>
            <tr>
                <td>Average Win</td>
                <td>${results.get('avg_win', 0):,.2f}</td>
            </tr>
            <tr>
                <td>Average Loss</td>
                <td>${results.get('avg_loss', 0):,.2f}</td>
            </tr>
            <tr>
                <td>Gross Profit</td>
                <td>${results.get('gross_profit', 0):,.2f}</td>
            </tr>
            <tr>
                <td>Gross Loss</td>
                <td>${results.get('gross_loss', 0):,.2f}</td>
            </tr>
        </table>

        <h2>Configuration</h2>
        <pre style="background-color: #f5f5f5; padding: 15px; border-radius: 4px; overflow-x: auto;">
{json.dumps(results.get('config', {}), indent=2)}
        </pre>

        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
            <p>Generated by Trading Bot Backtest Engine</p>
        </div>
    </div>
</body>
</html>
"""

        # Write HTML file
        output_file = output_path / f"{results.get('job_id', 'report')}.html"
        with open(output_file, 'w') as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {output_file}")
        return str(output_file)