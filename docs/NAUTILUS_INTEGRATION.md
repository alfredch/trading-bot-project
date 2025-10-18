# 🚀 Nautilus Trading Strategy Integration

## Übersicht

Vollständige Integration einer **echten Trading-Strategie** mit **Nautilus Trader** in das bestehende System.

### ✅ Was implementiert wurde:

1. **Mean Reversion Strategy mit Nautilus**
   - Proper Nautilus `Strategy` Base Class
   - Event-driven Bar Handling
   - Order Execution & Position Management
   
2. **Advanced Indicators**
   - Nadaraya-Watson Kernel Regression Bands
   - Support/Resistance Level Detection
   
3. **Nautilus Backtest Runner**
   - Echte Nautilus BacktestEngine
   - Data Preparation & Wrangling
   - Performance Metrics Extraction
   
4. **Integration in Backtest Engine**
   - Replace Mock mit echtem Nautilus
   - Fallback für Errors
   - Complete Results Pipeline

---

## 📁 Neue/Geänderte Dateien

### Core Strategy
```
services/nautilus_backtest/strategies/mean_reversion_nw.py
```
- **NEU**: Vollständige Nautilus Strategy Implementation
- Erbt von `nautilus_trader.trading.strategy.Strategy`
- Implementiert: `on_start()`, `on_bar()`, `on_stop()`, `on_reset()`
- Entry Logic: Lower Band + Support / Upper Band + Resistance
- Exit Logic: Mean Reversion to NW Center

### Backtest Runner
```
services/nautilus_backtest/src/nautilus_runner.py
```
- **NEU**: Nautilus Backtest Orchestration
- Creates Instruments, Venues, Accounts
- Data Wrangling (DataFrame → QuoteTicks)
- Results Extraction

### Updated Engine
```
services/nautilus_backtest/src/backtest_engine.py
```
- **UPDATED**: Ersetzt Mock durch echten Nautilus
- Imports `NautilusBacktestRunner`
- Strategy Class Loading
- Error Handling mit Fallback

### Dependencies
```
services/nautilus_backtest/requirements.piptools
```
- Nautilus Trader >= 1.220.0
- Scikit-learn für Clustering
- Scipy für Berechnungen

---

## 🎯 Strategy Details

### Mean Reversion with Nadaraya-Watson

**Konzept:**
- Price mean reversion basierend auf NW Kernel Regression
- S/R Levels für Entry Confirmation
- Exit bei Rückkehr zum Mean

**Entry Signals:**

**LONG Entry:**
```python
if price <= lower_band AND near_support_level:
    → BUY
```

**SHORT Entry:**
```python
if price >= upper_band AND near_resistance_level:
    → SELL
```

**Exit Signal:**
```python
if abs(price - nw_center) < threshold:
    → CLOSE POSITION
```

### Indicator Details

#### 1. Nadaraya-Watson Bands
```python
NadarayaWatsonBands(
    bandwidth=20.0,    # Kernel smoothing
    num_std=2.0        # Band width
)
```

- **Gaussian Kernel** für smooth price estimation
- **Adaptive Bands** basierend auf Volatilität
- **Center Line** als Mean Reversion Target

#### 2. Support/Resistance Levels
```python
SupportResistanceLevels(
    lookback=100,      # Historical bars
    n_clusters=5,      # Number of levels
    tolerance=0.02     # Level proximity
)
```

- **Pivot Detection** (Local Min/Max)
- **Agglomerative Clustering** für Level-Grouping
- **Dynamic Updates** mit neuen Bars

---

## 🔧 Configuration

### Strategy Config
```json
{
  "name": "mean_reversion_nw",
  "config": {
    "nw_bandwidth": 20.0,
    "nw_std": 2.0,
    "sr_lookback": 100,
    "sr_clusters": 5,
    "position_size": 1,
    "max_position": 2,
    "stop_loss_pct": 0.02,
    "take_profit_pct": 0.04,
    "warmup_period": 100,
    "initial_capital": 100000.0
  }
}
```

### Backtest Job Submission
```bash
curl -X POST http://localhost:8000/api/jobs/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {
      "name": "mean_reversion_nw",
      "run_id": 10,
      "instrument_id": 643,
      "start_date": "2024-01-01",
      "end_date": "2024-01-31",
      "config": {
        "nw_bandwidth": 20.0,
        "position_size": 1,
        "initial_capital": 100000.0
      }
    }
  }'
```

---

## 🧪 Testing

### Run Integration Tests
```bash
# In nautilus_backtest container
chmod +x /app/test-nautilus-strategy.sh
./test-nautilus-strategy.sh
```

**Tests:**
1. ✅ Indicator Functionality
2. ✅ Nautilus Runner Import
3. ✅ Strategy Initialization
4. ✅ Mini Backtest with Synthetic Data

### Manual Strategy Test
```python
from strategies.mean_reversion_nw import MeanReversionNWStrategy

config = {
    'instrument_id': 'TEST.SIM',
    'nw_bandwidth': 20.0,
    'position_size': 1
}

strategy = MeanReversionNWStrategy(config)
# Strategy ready for Nautilus
```

---

## 📊 Results Format

### Backtest Results
```json
{
  "status": "completed",
  "job_id": "backtest_abc123",
  "strategy": "mean_reversion_nw",
  "instrument": "RUN10_INST643",
  "ticks_processed": 1234567,
  
  "total_trades": 42,
  "winning_trades": 28,
  "losing_trades": 14,
  "win_rate": 66.67,
  
  "total_pnl": 12500.00,
  "gross_profit": 15000.00,
  "gross_loss": -2500.00,
  "avg_trade": 297.62,
  "profit_factor": 6.00,
  
  "final_balance": 112500.00,
  "final_equity": 112500.00,
  "return_pct": 12.50,
  
  "orders": [...],
  "positions": [...]
}
```

---

## 🚀 Deployment

### Update Container
```bash
# Rebuild nautilus_backtest service
make build-nautilus

# Or full rebuild
docker-compose build nautilus_backtest

# Restart service
docker-compose restart nautilus_backtest
```

### Verify Installation
```bash
# Check logs
docker-compose logs -f nautilus_backtest

# Should see:
# "Backtest engine initialized with Nautilus Trader"
```

---

## 📈 Performance Optimizations

### Data Loading
- ✅ Partitioned Parquet reads
- ✅ Date range filtering
- ✅ Efficient DataFrame operations

### Strategy Execution
- ✅ Buffer management (max 2x warmup)
- ✅ Indicator caching
- ✅ Vectorized calculations

### Memory Management
- ✅ Rolling windows
- ✅ Incremental processing
- ✅ Garbage collection hints

---

## 🐛 Troubleshooting

### Issue: "Nautilus not available"
**Solution:**
- Check `requirements.txt` installed
- Verify Nautilus version >= 1.220.0
```bash
pip list | grep nautilus-trader
```

### Issue: "No data found"
**Solution:**
- Verify Parquet files exist
- Check date range in job config
```bash
ls -la /data/parquet/RUN10_INST643/
```

### Issue: "Strategy import error"
**Solution:**
- Ensure Python path includes `/app`
- Check strategy file syntax
```bash
python3 -c "from strategies.mean_reversion_nw import MeanReversionNWStrategy"
```

### Issue: "Mock backtest running"
**Solution:**
- Nautilus import failed
- Check container logs for errors
- Verify all dependencies installed

---

## 🎓 Next Steps

### 1. **Add More Strategies**
```python
# Create new strategy file
strategies/momentum_breakout.py

class MomentumBreakoutStrategy(Strategy):
    ...
```

### 2. **Advanced Indicators**
- RSI, MACD, Bollinger Bands
- Custom ML-based indicators
- Multi-timeframe analysis

### 3. **Risk Management**
- Stop-loss automation
- Position sizing optimization
- Portfolio-level risk controls

### 4. **Optimization**
- Parameter grid search
- Walk-forward analysis
- Monte Carlo simulation

### 5. **Live Trading**
- Paper trading mode
- Real broker integration
- Real-time data feeds

---

## 📚 References

- [Nautilus Trader Docs](https://nautilustrader.io/)
- [Nadaraya-Watson Estimator](https://en.wikipedia.org/wiki/Kernel_regression)
- [Support/Resistance Trading](https://www.investopedia.com/trading/support-and-resistance-basics/)

---

## ✅ Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Strategy Class | ✅ Complete | Full Nautilus integration |
| Indicators | ✅ Complete | NW + S/R working |
| Backtest Runner | ✅ Complete | Real Nautilus execution |
| Engine Integration | ✅ Complete | Mock replaced |
| Testing | ✅ Complete | Integration tests ready |
| Documentation | ✅ Complete | This file! |

**Ready for production backtesting! 🎉**