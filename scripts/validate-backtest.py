# scripts/validate-backtest.py
# !/usr/bin/env python3
"""Validate backtest results"""
import sys
import json
from pathlib import Path


def validate_results(job_id: str):
    results_file = Path(f"data/results/{job_id}.json")

    if not results_file.exists():
        print(f"❌ Results not found: {results_file}")
        return False

    with open(results_file) as f:
        results = json.load(f)

    print('═' * 60)
    print('✅ BACKTEST RESULTS')
    print('═' * 60)
    print(f"Job ID: {results.get('job_id')}")
    print(f"Strategy: {results.get('strategy')}")
    print(f"Instrument: {results.get('instrument')}")
    print(f"Period: {results.get('start_date')} to {results.get('end_date')}")
    print()
    print('─' * 60)
    print('PERFORMANCE METRICS')
    print('─' * 60)
    print(f"Total Trades: {results.get('total_trades', 0)}")
    print(f"Win Rate: {results.get('win_rate', 0):.2f}%")
    print(f"Total PnL: ${results.get('total_pnl', 0):,.2f}")
    print(f"Profit Factor: {results.get('profit_factor', 0):.2f}")
    print(f"Max Drawdown: ${results.get('max_drawdown', 0):,.2f}")
    print(f"Sharpe Ratio: {results.get('sharpe_ratio', 0):.2f}")
    print(f"Ticks Processed: {results.get('ticks_processed', 0):,}")
    print('═' * 60)

    return True


if __name__ == '__main__':
    job_id = sys.argv[1] if len(sys.argv) > 1 else None

    if not job_id:
        # Find latest
        results_dir = Path('data/results')
        files = sorted(results_dir.glob('backtest*.json'), key=lambda x: x.stat().st_mtime, reverse=True)
        if files:
            job_id = files[0].stem
        else:
            print("No backtest results found")
            sys.exit(1)

    validate_results(job_id)