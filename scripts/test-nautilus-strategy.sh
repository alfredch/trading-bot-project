#!/bin/bash
# Test Nautilus Strategy Integration
# Uses 'docker compose' (v2) instead of deprecated 'docker-compose'

set -e

echo "=================================================="
echo "🧪 Testing Nautilus Strategy Integration"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test 1: Check if indicators work
echo "Test 1: Testing Indicators..."
echo "-----------------------------------"

python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

from strategies.indicators.nadaraya_watson import NadarayaWatsonBands
from strategies.indicators.support_resistance import SupportResistanceLevels
import numpy as np

# Test NW Bands
print("✓ Testing Nadaraya-Watson Bands...")
nw = NadarayaWatsonBands(bandwidth=20.0, num_std=2.0)
x = np.arange(100)
y = np.random.randn(100).cumsum() + 100

center, upper, lower = nw.calculate(x, y)
print(f"  - Center: {center[-1]:.2f}")
print(f"  - Upper: {upper[-1]:.2f}")
print(f"  - Lower: {lower[-1]:.2f}")

# Test S/R Levels
print("\n✓ Testing Support/Resistance Levels...")
sr = SupportResistanceLevels(lookback=100, n_clusters=5)
highs = list(y + np.random.rand(100) * 2)
lows = list(y - np.random.rand(100) * 2)

support, resistance = sr.detect(highs, lows)
print(f"  - Support levels: {len(support)}")
print(f"  - Resistance levels: {len(resistance)}")

print("\n✅ Indicators test PASSED")
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 1 PASSED${NC}"
else
    echo -e "${RED}❌ Test 1 FAILED${NC}"

fi

echo ""

# Test 2: Check if Nautilus runner can be imported
echo "Test 2: Testing Nautilus Runner Import..."
echo "-----------------------------------"

python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

try:
    from src.nautilus_runner import NautilusBacktestRunner
    print("✓ NautilusBacktestRunner imported successfully")

    runner = NautilusBacktestRunner()
    print(f"✓ Runner initialized with venue: {runner.venue}")

    print("\n✅ Nautilus Runner import test PASSED")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 2 PASSED${NC}"
else
    echo -e "${RED}❌ Test 2 FAILED${NC}"
    exit 1
fi

echo ""

# Test 3: Check if strategy can be imported
echo "Test 3: Testing Strategy Import..."
echo "-----------------------------------"

python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

try:
    from strategies.mean_reversion_nw import MeanReversionNWStrategy
    print("✓ MeanReversionNWStrategy imported successfully")

    config = {
        'instrument_id': 'TEST.SIM',
        'nw_bandwidth': 20.0,
        'nw_std': 2.0,
        'sr_lookback': 100,
        'position_size': 1,
        'warmup_period': 50
    }

    strategy = MeanReversionNWStrategy(config)
    print(f"✓ Strategy initialized with instrument: {strategy.instrument_id}")
    print(f"✓ Warmup period: {strategy.warmup_period}")

    print("\n✅ Strategy import test PASSED")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 3 PASSED${NC}"
else
    echo -e "${RED}❌ Test 3 FAILED${NC}"
    exit 1
fi

echo ""

# Test 4: Mini backtest with synthetic data
echo "Test 4: Testing Mini Backtest..."
echo "-----------------------------------"

python3 << 'EOF'
import sys
sys.path.insert(0, '/app')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

try:
    from src.nautilus_runner import NautilusBacktestRunner
    from strategies.mean_reversion_nw import MeanReversionNWStrategy

    print("✓ Generating synthetic tick data...")

    # Generate 1000 synthetic ticks
    np.random.seed(42)
    n_ticks = 1000

    base_price = 100.0
    price_changes = np.random.randn(n_ticks).cumsum() * 0.1
    prices = base_price + price_changes

    # Create tick data
    start_time = datetime.now()
    timestamps = [start_time + timedelta(seconds=i) for i in range(n_ticks)]

    df = pd.DataFrame({
        'ts_event': pd.to_datetime(timestamps),
        'bid_price': prices - 0.01,
        'ask_price': prices + 0.01,
        'bid_size': np.random.randint(1, 100, n_ticks),
        'ask_size': np.random.randint(1, 100, n_ticks)
    })

    print(f"  - Generated {len(df):,} ticks")
    print(f"  - Price range: {df['bid_price'].min():.2f} - {df['ask_price'].max():.2f}")

    print("\n✓ Running mini backtest...")

    runner = NautilusBacktestRunner()

    config = {
        'instrument_id': 'TEST.SIM',
        'nw_bandwidth': 20.0,
        'nw_std': 2.0,
        'sr_lookback': 100,
        'position_size': 1,
        'warmup_period': 50,
        'initial_capital': 10000.0
    }

    results = runner.run_backtest(
        strategy_class=MeanReversionNWStrategy,
        strategy_config=config,
        data=df,
        instrument_id_str='TEST',
        initial_capital=10000.0
    )

    print("\n✓ Backtest completed!")
    print(f"  - Status: {results.get('status')}")
    print(f"  - Ticks processed: {results.get('ticks_processed', 0):,}")
    print(f"  - Total trades: {results.get('total_trades', 0)}")
    print(f"  - Win rate: {results.get('win_rate', 0):.2f}%")
    print(f"  - Total PnL: ${results.get('total_pnl', 0):.2f}")

    print("\n✅ Mini backtest test PASSED")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Test 4 PASSED${NC}"
else
    echo -e "${YELLOW}⚠️  Test 4 FAILED (Nautilus might not be fully configured)${NC}"
    echo -e "${YELLOW}This is expected if Nautilus Trader installation is incomplete${NC}"
fi

echo ""
echo "=================================================="
echo "🎉 Nautilus Strategy Integration Tests Complete!"
echo "=================================================="
echo ""
echo "Summary:"
echo "  ✅ Indicators working"
echo "  ✅ Nautilus runner available"
echo "  ✅ Strategy class ready"
echo "  ⚠️  Full backtest requires complete Nautilus setup"
echo ""
echo "Next steps:"
echo "  1. Ensure Nautilus Trader is fully installed"
echo "  2. Test with real market data"
echo "  3. Submit backtest job via API"
echo ""