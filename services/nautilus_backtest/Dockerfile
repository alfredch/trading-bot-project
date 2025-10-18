ARG PYTHON_VERSION=3.12
FROM python:${PYTHON_VERSION}-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# FIX: Remove executable stack flag
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends patchelf findutils; \
    for so in $(find /usr/local/lib -type f -path "*/site-packages/nautilus_trader/backtest/engine*.so"); do \
        echo "Clearing execstack on: $so"; \
        patchelf --clear-execstack "$so"; \
    done; \
    apt-get purge -y --auto-remove patchelf; \
    rm -rf /var/lib/apt/lists/*

# Copy application code from correct paths (relative to project root)
COPY services/nautilus_backtest/src/ /app/src/
COPY services/nautilus_backtest/strategies/ /app/strategies/

# Setup Python path
ENV PYTHONPATH=/app:/app/src

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import nautilus_trader; import redis; r=redis.Redis(host='redis', socket_connect_timeout=5); r.ping()" || exit 1

CMD ["python", "-u", "src/main.py"]