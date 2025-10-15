# scripts/test-database.sh
#!/bin/bash

PROJECT_NAME="trading_bot"

echo "=== Testing Database Access ==="
echo

# 1. Check row count
echo "1. Row count in training_ticks:"
docker compose -p $PROJECT_NAME exec -T postgres psql -U ts_admin -d trading_data -c \
  "SELECT COUNT(*) FROM training_ticks;"
echo

# 2. Show instruments
echo "2. Available run_ids:"
docker compose -p $PROJECT_NAME exec -T postgres psql -U ts_admin -d trading_data -c \
  "SELECT DISTINCT run_id, COUNT(*) as row_count FROM training_ticks GROUP BY run_id;"
echo

# 3. Date range
echo "3. Date range:"
docker compose -p $PROJECT_NAME exec -T postgres psql -U ts_admin -d trading_data -c \
  "SELECT MIN(time) as first_date, MAX(time) as last_date FROM training_ticks where run_id=10;"
echo

# 4. Sample data
echo "4. Sample rows:"
docker compose -p $PROJECT_NAME exec -T postgres psql -U ts_admin -d trading_data -c \
  "SELECT * FROM training_ticks where run_id=10 ORDER BY time LIMIT 3;"