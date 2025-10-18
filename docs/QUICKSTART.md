# 🚀 Quick Start: Nautilus Trading Strategy

## In 5 Minuten zum ersten Backtest!

### Schritt 1: Files aktualisieren

Ersetze folgende Files in deinem Projekt:

```bash
# 1. Strategy (vollständig neu)
services/nautilus_backtest/strategies/mean_reversion_nw.py

# 2. Neuer Backtest Runner
services/nautilus_backtest/src/nautilus_runner.py

# 3. Updated Engine
services/nautilus_backtest/src/backtest_engine.py

# 4. Test Script
scripts/test-nautilus-strategy.sh
```

### Schritt 2: Container neu bauen

```bash
# Stop services
docker-compose down nautilus_backtest

# Rebuild
docker-compose build nautilus_backtest

# Start
docker-compose up -d nautilus_backtest

# Check logs
docker-compose logs -f nautilus_backtest
```

**Erwartete Log-Ausgabe:**
```
nautilus_backtest | Backtest engine initialized with Nautilus Trader
nautilus_backtest | Backtest engine started. Waiting for jobs...
```

### Schritt 3: Test ausführen

```bash
# In nautilus container
docker-compose exec nautilus_backtest bash

# Run tests
chmod +x /app/test-nautilus-strategy.sh
./test-nautilus-strategy.sh
```

**Erwartete Ausgabe:**
```
🧪 Testing Nautilus Strategy Integration
✅ Test 1 PASSED (Indicators)
✅ Test 2 PASSED (Nautilus Runner)
✅ Test 3 PASSED (Strategy Import)
⚠️  Test 4 PASSED (Mini Backtest)
```

### Schritt 4: Ersten Backtest starten

```bash
# Submit backtest job via API
curl -X POST http://localhost:8000/api/jobs/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {
      "name": "mean_reversion_nw",
      "run_id": 10,
      "instrument_id": 643,
      "start_date": "2024-01-01",
      "end_date": "2024-01-07",
      "config": {
        "nw_bandwidth": 20.0,
        "nw_std": 2.0,
        "sr_lookback": 100,
        "position_size": 1,
        "warmup_period": 100,
        "initial_capital": 100000.0
      }
    }
  }'
```

### Schritt 5: Results abrufen

```bash
# Get job status
curl http://localhost:8000/api/jobs/{job_id}

# Check results file
ls -la data/results/
cat data/results/{job_id}.json
```

---

## 📊 Results verstehen

```json
{
  "total_trades": 42,        // Anzahl Trades
  "winning_trades": 28,      // Profitable Trades
  "losing_trades": 14,       // Verlust Trades
  "win_rate": 66.67,         // Win Rate %
  
  "total_pnl": 12500.00,     // Gesamt Profit/Loss
  "gross_profit": 15000.00,  // Summe Gewinne
  "gross_loss": -2500.00,    // Summe Verluste
  
  "avg_trade": 297.62,       // Durchschnitt pro Trade
  "avg_win": 535.71,         // Durchschnitt Gewinn
  "avg_loss": -178.57,       // Durchschnitt Verlust
  
  "profit_factor": 6.00,     // Gross Profit / Gross Loss
  
  "final_balance": 112500.00,// End Balance
  "return_pct": 12.50        // Return %
}
```

---

## 🎯 Strategy Parameter Tuning

### Conservative Setup (weniger Trades, höhere Qualität)
```json
{
  "nw_bandwidth": 30.0,      // Mehr Smoothing
  "nw_std": 2.5,             // Weitere Bands
  "sr_lookback": 200,        // Mehr Historie
  "warmup_period": 200
}
```

### Aggressive Setup (mehr Trades, höheres Risiko)
```json
{
  "nw_bandwidth": 10.0,      // Weniger Smoothing
  "nw_std": 1.5,             // Engere Bands
  "sr_lookback": 50,         // Weniger Historie
  "warmup_period": 50
}
```

### Balanced Setup (empfohlen)
```json
{
  "nw_bandwidth": 20.0,
  "nw_std": 2.0,
  "sr_lookback": 100,
  "warmup_period": 100
}
```

---

## 🔥 Häufige Probleme & Lösungen

### Problem: "Mock backtest running"
```bash
# Check Nautilus installation
docker-compose exec nautilus_backtest pip list | grep nautilus

# Reinstall if needed
docker-compose exec nautilus_backtest pip install nautilus-trader>=1.220.0

# Restart
docker-compose restart nautilus_backtest
```

### Problem: "No data found"
```bash
# Check if data exists
docker-compose exec nautilus_backtest ls -la /data/parquet/RUN10_INST643/

# Check date range
docker-compose exec nautilus_backtest ls /data/parquet/RUN10_INST643/ | grep date=
```

### Problem: "Strategy import error"
```bash
# Test import manually
docker-compose exec nautilus_backtest python3 << EOF
import sys
sys.path.insert(0, '/app')
from strategies.mean_reversion_nw import MeanReversionNWStrategy
print("✅ Import successful")
EOF
```

---

## 📈 Performance Monitoring

### Watch Backtest Logs
```bash
docker-compose logs -f nautilus_backtest | grep -E "(LONG|SHORT|EXIT|signal)"
```

### Check Processing Speed
```bash
# Should process ~10,000-50,000 ticks/second
docker-compose logs nautilus_backtest | grep "Processed.*bars"
```

### Monitor Resources
```bash
docker stats nautilus_backtest
```

---

## 🎓 Nächste Schritte

### 1. **Parameter Optimization**
```bash
# Run multiple backtests with different parameters
for bandwidth in 10 15 20 25 30; do
  curl -X POST http://localhost:8000/api/jobs/backtest \
    -H "Content-Type: application/json" \
    -d "{
      \"strategy\": {
        \"name\": \"mean_reversion_nw\",
        \"run_id\": 10,
        \"instrument_id\": 643,
        \"start_date\": \"2024-01-01\",
        \"end_date\": \"2024-01-31\",
        \"config\": {
          \"nw_bandwidth\": $bandwidth,
          \"position_size\": 1
        }
      }
    }"
done
```

### 2. **Multi-Instrument Testing**
```bash
# Test across multiple instruments
for inst in 643 644 645; do
  # Submit backtest for each instrument
  curl -X POST http://localhost:8000/api/jobs/backtest \
    -d "{\"strategy\": {\"instrument_id\": $inst, ...}}"
done
```

### 3. **Walk-Forward Analysis**
```bash
# Test on different time periods
dates=(
  "2024-01-01:2024-01-07"
  "2024-01-08:2024-01-14"
  "2024-01-15:2024-01-21"
  "2024-01-22:2024-01-31"
)

for date_range in "${dates[@]}"; do
  start=${date_range%:*}
  end=${date_range#*:}
  # Submit backtest for each period
done
```

### 4. **Results Analysis Script**
```python
# analyze_results.py
import json
import pandas as pd
from pathlib import Path

# Load all results
results_path = Path('/data/results')
results = []

for file in results_path.glob('*.json'):
    with open(file) as f:
        data = json.load(f)
        results.append(data)

# Create DataFrame
df = pd.DataFrame(results)

# Analyze
print("Top 5 by Total PnL:")
print(df.nlargest(5, 'total_pnl')[['strategy', 'instrument', 'total_pnl', 'win_rate']])

print("\nTop 5 by Win Rate:")
print(df.nlargest(5, 'win_rate')[['strategy', 'instrument', 'win_rate', 'total_trades']])

print("\nTop 5 by Profit Factor:")
print(df.nlargest(5, 'profit_factor')[['strategy', 'instrument', 'profit_factor', 'total_pnl']])
```

---

## 🔍 Advanced: Custom Strategy Development

### Create New Strategy

```python
# services/nautilus_backtest/strategies/your_strategy.py

from nautilus_trader.trading.strategy import Strategy
from nautilus_trader.model.data import Bar

class YourCustomStrategy(Strategy):
    
    def __init__(self, config: dict = None):
        super().__init__(config)
        # Your initialization
        
    def on_start(self):
        self.instrument = self.cache.instrument(self.instrument_id)
        self.subscribe_bars(self.bar_type)
        
    def on_bar(self, bar: Bar):
        # Your trading logic
        price = float(bar.close)
        
        # Example: Simple moving average crossover
        if self.sma_fast[-1] > self.sma_slow[-1]:
            self._enter_long(price)
        elif self.sma_fast[-1] < self.sma_slow[-1]:
            self._enter_short(price)
```

### Register Strategy

```python
# In backtest_engine.py, update strategy_map:

strategy_map = {
    'mean_reversion_nw': MeanReversionNWStrategy,
    'your_strategy': YourCustomStrategy,  # Add here
}
```

### Test Your Strategy

```bash
curl -X POST http://localhost:8000/api/jobs/backtest \
  -d '{
    "strategy": {
      "name": "your_strategy",
      ...
    }
  }'
```

---

## 📊 Grafana Dashboard Integration

### Add Backtest Metrics

```bash
# In Grafana, create new panel:
# Query: backtest_results_total
# Labels: strategy, instrument, result

# Visualization:
# - Bar chart: Win Rate by Strategy
# - Time series: PnL over time
# - Table: Top performing configs
```

### Custom Metrics

```python
# In strategy, add metrics:
from prometheus_client import Counter, Gauge

trade_counter = Counter('strategy_trades_total', 'Total trades', ['strategy', 'side'])
pnl_gauge = Gauge('strategy_pnl', 'Current PnL', ['strategy'])

def _enter_long(self, price):
    trade_counter.labels(strategy='mean_reversion', side='long').inc()
    # ... rest of logic
```

---

## 🎯 Production Checklist

- [ ] Tests passed (`test-nautilus-strategy.sh`)
- [ ] Strategy validated on historical data
- [ ] Parameter optimization completed
- [ ] Walk-forward analysis shows consistency
- [ ] Risk management rules implemented
- [ ] Stop-loss / Take-profit configured
- [ ] Position sizing validated
- [ ] Multiple instruments tested
- [ ] Results documented
- [ ] Monitoring dashboards configured
- [ ] Alert rules defined
- [ ] Backup strategy in place

---

## 💡 Pro Tips

### 1. **Warmup Period**
```python
# Always use adequate warmup
warmup_period = max(
    nw_bandwidth * 5,  # 5x bandwidth for NW
    sr_lookback,       # Full lookback for S/R
    100                # Minimum 100 bars
)
```

### 2. **Data Quality**
```python
# Check data before backtest
df = loader.load_instrument_data(...)

# Validate
assert len(df) > 0, "No data"
assert df['bid_price'].notna().all(), "Missing bids"
assert df['ask_price'].notna().all(), "Missing asks"
assert (df['ask_price'] >= df['bid_price']).all(), "Spread negative"
```

### 3. **Result Validation**
```python
# Sanity checks
assert results['total_trades'] >= 0
assert results['winning_trades'] + results['losing_trades'] == results['total_trades']
assert abs(results['gross_profit'] + results['gross_loss'] - results['total_pnl']) < 0.01
```

### 4. **Performance Optimization**
```python
# Use limited data for development
if development_mode:
    df = df.head(10000)  # Only 10k ticks
    config['warmup_period'] = 50  # Faster warmup
```

---

## 🚨 Common Pitfalls

### ❌ Don't: Look-ahead Bias
```python
# WRONG - uses future data
if self.prices[i+1] > self.prices[i]:
    self._enter_long()
```

### ✅ Do: Use only past data
```python
# CORRECT - only past/current
if self.prices[-1] > self.prices[-2]:
    self._enter_long()
```

### ❌ Don't: Overfitting
```python
# WRONG - too many parameters
config = {
    'param1': 1.234,
    'param2': 5.678,
    'param3': 9.012,
    # ... 20 more params
}
```

### ✅ Do: Keep it simple
```python
# CORRECT - few key parameters
config = {
    'nw_bandwidth': 20.0,
    'position_size': 1,
    'stop_loss_pct': 0.02
}
```

### ❌ Don't: Ignore transaction costs
```python
# WRONG - no slippage/fees
profit = exit_price - entry_price
```

### ✅ Do: Include realistic costs
```python
# CORRECT - with costs
profit = (exit_price - entry_price) - commission - slippage
```

---

## 📚 Resources

### Documentation
- **Nautilus Trader**: https://nautilustrader.io/docs/
- **Strategy Development**: https://nautilustrader.io/docs/concepts/strategies
- **Backtesting**: https://nautilustrader.io/docs/concepts/backtesting

### Examples
- **Official Examples**: https://github.com/nautechsystems/nautilus_trader/tree/develop/examples
- **Community Strategies**: https://github.com/nautechsystems/nautilus_trader/discussions

### Support
- **Discord**: https://discord.gg/nautilus
- **GitHub Issues**: https://github.com/nautechsystems/nautilus_trader/issues

---

## ✅ Summary

| Task | Command | Expected Result |
|------|---------|-----------------|
| Update files | Copy new strategy files | ✅ Files in place |
| Rebuild | `docker-compose build` | ✅ Container rebuilt |
| Test | `./test-nautilus-strategy.sh` | ✅ All tests pass |
| Run backtest | `curl POST /api/jobs/backtest` | ✅ Job submitted |
| Check results | `cat data/results/*.json` | ✅ Results saved |

**You're ready to trade! 🎉**

---

## 🆘 Need Help?

```bash
# Check this guide
cat QUICKSTART.md

# Check full documentation
cat NAUTILUS_INTEGRATION.md

# Check logs
docker-compose logs -f nautilus_backtest

# Run diagnostics
./test-nautilus-strategy.sh

# Check health
curl http://localhost:8000/health
```

**Happy Trading! 📈💰**