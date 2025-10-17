include Makefile.monitoring

.PHONY: help setup start stop restart logs ps clean test health scale

COMPOSE_PROJECT_NAME := trading_bot
COMPOSE_FILE := docker-compose.yml
COMPOSE_DEV := docker-compose.dev.yml
DOCKER_COMPOSE := docker compose

help:
	@echo "Trading Bot - Management Commands"
	@echo "=================================="
	@echo ""
	@echo "Setup & Installation:"
	@echo "  setup          - Initial project setup"
	@echo "  check          - Check Docker environment"
	@echo ""
	@echo "Service Management:"
	@echo "  start          - Start core services"
	@echo "  start-dev      - Start in development mode"
	@echo "  start-all      - Start all services including workers"
	@echo "  stop           - Stop all services"
	@echo "  restart        - Restart services"
	@echo "  status         - Show detailed system status"
	@echo "  health         - Run health check"
	@echo "  ps             - Show running containers"
	@echo ""
	@echo "Workers & Pipeline:"
	@echo "  start-workers  - Start worker services"
	@echo "  start-pipeline - Start data pipeline"
	@echo "  start-backtest - Start backtest service"
	@echo "  scale          - Scale workers (use workers=N)"
	@echo ""
	@echo "Logs & Debugging:"
	@echo "  logs           - Show logs (use service=<name>)"
	@echo "  logs-watch     - Interactive log viewer"
	@echo "  shell          - Open shell (use service=<name>)"
	@echo ""
	@echo "Data Management:"
	@echo "  migrate        - Run data migration"
	@echo "  backtest       - Run backtest"
	@echo "  backup         - Backup data and databases"
	@echo ""
	@echo "Maintenance:"
	@echo "  build          - Build all images"
	@echo "  pull           - Pull latest images"
	@echo "  update         - Update system"
	@echo "  clean          - Interactive cleanup"
	@echo "  clean-full     - Remove everything (⚠ data loss)"
	@echo "  test           - Run tests"
	@echo ""
	@echo "Examples:"
	@echo "  make start"
	@echo "  make logs service=api"
	@echo "  make scale workers=4"
	@echo "  make shell service=worker"

check:
	@bash scripts/check-docker.sh

setup:
	@bash scripts/setup.sh

start:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) up -d postgres redis api
	@echo "Core services started."
	@echo "Use 'make status' to check health"

start-dev:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up -d

start-all:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) --profile workers --profile pipeline --profile backtest up -d

start-workers:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) --profile workers up -d

start-pipeline:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) --profile pipeline up -d

start-backtest:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) --profile backtest up -d

stop:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) stop

restart:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) restart $(service)

health:
	@bash scripts/health-check.sh

ps:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) ps

logs:
ifdef service
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) logs -f --tail=100 $(service)
else
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) logs -f --tail=100
endif

logs-watch:
	@bash scripts/logs-watch.sh $(service)

shell:
ifdef service
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) exec $(service) /bin/bash
else
	@echo "Please specify service: make shell service=api"
endif

scale:
ifdef workers
	@bash scripts/scale-workers.sh $(workers)
else
	@echo "Please specify number of workers: make scale workers=4"
endif

migrate:
	@bash scripts/migrate_data.sh

backtest:
	@bash scripts/manage.sh backtest

backup:
	@bash scripts/backup.sh

build:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) build

build-no-cache:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) build --no-cache

pull:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) pull

update:
	@bash scripts/update.sh

clean:
	@bash scripts/cleanup.sh

clean-full:
	@echo "⚠️  This will remove all containers, networks, volumes, and images!"
	@read -p "Type 'DELETE' to confirm: " confirm && [ "$$confirm" = "DELETE" ]
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) down -v --rmi all
	@echo "✓ Complete cleanup done"

test:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) exec api pytest tests/ -v
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) exec nautilus_backtest pytest tests/ -v

# Development helpers
dev-rebuild:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) -f $(COMPOSE_FILE) -f $(COMPOSE_DEV) up -d --build

dev-logs:
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) logs -f api worker

# Worker management
scale-workers:
ifdef workers
	@echo "Scaling workers to $(workers) instances..."
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) up -d --scale worker=$(workers) --no-recreate
	@echo "✓ Workers scaled to $(workers)"
	@$(DOCKER_COMPOSE) -p $(COMPOSE_PROJECT_NAME) ps worker
else
	@echo "Usage: make scale-workers workers=N"
endif

worker-metrics:
	@echo "=== Worker Metrics ==="
	@docker exec trading_bot_redis redis-cli --raw KEYS "worker:*:metrics" | \
		xargs -I {} docker exec trading_bot_redis redis-cli HGETALL {}

worker-heartbeats:
	@echo "=== Worker Heartbeats ==="
	@docker exec trading_bot_redis redis-cli --raw KEYS "worker:*:heartbeat" | \
		xargs -I {} sh -c 'echo "{}:" && docker exec trading_bot_redis redis-cli GET {}'

dlq-list:
	@echo "=== Dead Letter Queue ==="
	@docker exec trading_bot_redis redis-cli LRANGE queue:dlq 0 -1

dlq-retry:
ifdef job_id
	@echo "Retrying job $(job_id) from DLQ..."
	@docker exec trading_bot_redis redis-cli LREM queue:dlq 1 $(job_id)
	@# Determine job type and requeue
	@docker exec trading_bot_redis redis-cli LPUSH queue:migration $(job_id)
else
	@echo "Usage: make dlq-retry job_id=<job_id>"
endif

# Add to Makefile

# === Quick Operations ===

# Full pipeline test
test-pipeline:
	@./scripts/full-pipeline-test.sh

# Latest backtest results
show-latest-backtest:
	@python scripts/validate-backtest.py

# List all results
list-results:
	@echo "=== Recent Migrations ==="
	@ls -lht data/parquet/ | head -10
	@echo
	@echo "=== Recent Backtests ==="
	@ls -lht data/results/*.json | head -10

# Compare multiple backtests
compare-backtests:
	@python scripts/compare-backtests.py

# System status
status:
	@echo "=== System Status ==="
	@docker compose -p $(COMPOSE_PROJECT_NAME) ps
	@echo
	@echo "=== API Health ==="
	@curl -s http://localhost:8010/health | jq
	@echo
	@echo "=== Recent Jobs ==="
	@curl -s http://localhost:8010/jobs?limit=5 | jq '.jobs[] | {job_id, status, progress}'

.SILENT: help