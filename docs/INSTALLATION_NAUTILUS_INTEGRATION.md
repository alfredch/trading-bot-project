# 📦 Installation Guide: Nautilus Trading Strategy

## Schritt-für-Schritt Anleitung zur Integration

### Voraussetzungen

- ✅ Docker & Docker Compose installiert
- ✅ Bestehendes Trading-Bot Projekt läuft
- ✅ Redis & PostgreSQL Services aktiv
- ✅ Data Pipeline mit Parquet Files vorhanden

---

## 🚀 Installation in 10 Minuten

### Schritt 1: Files herunterladen

Speichere die folgenden Files aus den Artifacts:

```
1. mean_reversion_nw.py          → services/nautilus_backtest/strategies/
2. nautilus_runner.py            → services/nautilus_backtest/src/
3. backtest_engine.py            → services/nautilus_backtest/src/
4. requirements.piptools         → services/nautilus_backtest/
5. test-nautilus-strategy.sh     → scripts/
6. NAUTILUS_INTEGRATION.md       → docs/
7. QUICKSTART.md                 → docs/
```

### Schritt 2: File Permissions

```bash
# Make test script executable
chmod +x scripts/test-nautilus-strategy.sh

# Verify file structure
tree services/nautilus_backtest/
```

**Expected structure:**
```
services/nautilus_backtest/
├── Dockerfile
├── requirements.piptools          ← Updated
├── requirements.txt               (will be regenerated)
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── data_loader.py
│   ├── backtest_engine.py        ← Updated
│   ├── nautilus_runner.py        ← NEW
│   └── ...
└── strategies/
    ├── __init__.py
    ├── mean_reversion_nw.py      ← Updated (full rewrite)
    └── indicators/
        ├── __init__.py
        ├── nadaraya_watson.py
        └── support_resistance.py
```

### Schritt 3: Requirements aktualisieren

```bash
# Navigate to nautilus service
cd services/nautilus_backtest/

# Regenerate requirements.txt from .piptools
docker run --rm -v $(pwd):/app python:3.11-slim bash -c "
  pip install uv && \
  cd /app && \
  uv pip compile requirements.piptools --output-file requirements.txt
"

# Or manually if you prefer:
# pip-compile requirements.piptools -o requirements.txt
```

### Schritt 4: Docker Container neu bauen

```bash
# Stop current nautilus service
docker-compose stop nautilus_backtest

# Rebuild container
docker-compose build nautilus_backtest

# Expected output:
# Successfully built...
# Successfully tagged trading-bot-project-nautilus_backtest:latest
```

**Troubleshooting:**
```bash
# If build fails, try clean build:
docker-compose build --no-cache nautilus_backtest

# Check build logs:
docker-compose build nautilus_backtest 2>&1 | tee build.log
```

### Schritt 5: Container starten

```bash
# Start nautilus service
docker-compose up -d nautilus_backtest

# Wait for initialization (5-10 seconds)
sleep 10

# Check if running
docker-compose ps nautilus_backtest
```

**Expected status:**
```
NAME                  STATE    PORTS
nautilus_backtest     Up       (healthy)
```

### Schritt 6: Logs prüfen

```bash
# Check container logs
docker-compose logs nautilus_backtest

# Look for these lines:
# ✅ "Backtest engine initialized with Nautilus Trader"
# ✅ "Backtest engine started. Waiting for jobs..."
```

**Good log example:**
```
nautilus_backtest | INFO - Nautilus Backtest Service starting...
nautilus_backtest | INFO - Backtest engine initialized with Nautilus Trader
nautilus_backtest | INFO - Backtest engine started. Waiting for jobs...
```

**Bad log example (needs fixing):**
```
nautilus_backtest | ERROR - Import error: No module named 'nautilus_trader'
nautilus_backtest | CRITICAL - Fatal error
```

### Schritt 7: Tests ausführen

```bash
# Enter container
docker-compose exec nautilus_backtest bash

# Run integration tests
cd /app
./test-nautilus-strategy.sh
```

**Expected output:**
```
🧪 Testing Nautilus Strategy Integration
==========================================

Test 1: Testing Indicators...
✅ Test 1 PASSED

Test 2: Testing Nautilus Runner Import...
✅ Test 2 PASSED

Test 3: Testing Strategy Import...
✅ Test 3 PASSED

Test 4: Testing Mini Backtest...
✅ Test 4 PASSED

🎉 All tests PASSED!
```

### Schritt 8: Ersten Backtest ausführen

```bash
# Exit container
exit

# Submit test backtest via API
curl -X POST http://localhost:8000/api/jobs/backtest \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": {
      "name": "mean_reversion_nw",
      "run_id": 10,
      "instrument_id": 643,
      "start_date": "2024-01-01",
      "end_date": "2024-01-02",
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

**Expected response:**
```json
{
  "job_id": "backtest_abc123def456",
  "status": "queued",
  "message": "Backtest job submitted"
}
```

### Schritt 9: Results prüfen

```bash
# Wait for backtest to complete (30-60 seconds)
sleep 60

# Check job status
curl http://localhost:8000/api/jobs/{job_id}

# View results file
cat data/results/{job_id}.json
```

**Good result:**
```json
{
  "status": "completed",
  "total_trades": 12,
  "winning_trades": 8,
  "losing_trades": 4,
  "win_rate": 66.67
}
```
