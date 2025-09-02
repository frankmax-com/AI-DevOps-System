# Multi-stage Dockerfile for Dev Agent Service
# Production-optimized container with security scanning

# ================================
# BUILD STAGE
# ================================
FROM python:3.9-slim AS builder

# Metadata
LABEL maintainer="AI DevOps System"
LABEL description="Dev Agent Service - Program Factory Worker"
LABEL version="0.1.0"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    POETRY_VERSION=1.3.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_NO_INTERACTION=1

# Install system dependencies for build
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        build-essential \
        libffi-dev \
        libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN curl -sSL https://install.python-poetry.org | python3 -
ENV PATH="${POETRY_HOME}/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY dev-agent-service/pyproject.toml dev-agent-service/poetry.lock ./

# Install dependencies with poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi --no-root

# ================================
# RUNTIME STAGE (SLIM PRODUCTION)
# ================================
FROM python:3.9-slim AS runtime

# Security hardening
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl \
        iptables \
        procps \
        net-tools \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r devagent -g 1000 \
    && useradd -r -u 1000 -g devagent devagent \
    && mkdir -p /app && chown devagent:devagent /app \
    && mkdir -p /app/logs && chown devagent:devagent /app/logs

# Non-root user
USER 1000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    SERVICE_NAME="dev-agent-service" \
    SERVICE_VERSION="0.1.0" \
    HOST="0.0.0.0" \
    PORT="8000" \
    PYTHONPATH="/app"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Working directory
WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY dev-agent-service/src/ ./src/
COPY dev-agent-service/templates/ ./templates/ 2>/dev/null || true
COPY dev-agent-service/scaffolds/ ./scaffolds/ 2>/dev/null || true

# Application port
EXPOSE ${PORT}

# Startup command with proper signal handling
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]

# ================================
# DEVELOPMENT STAGE (OPTIONAL)
# ================================
FROM runtime AS development

ENV PYTHONPATH="/app" \
    DEBUG="true"

# Switch back to root for development
USER root

# Install dev dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-cov \
    pytest-asyncio \
    black \
    isort \
    flake8 \
    uvicorn[standard]

# Development port
EXPOSE 8000 5678

# Auto-reload for development
CMD ["python", "-m", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "info"]

# ================================
# DEFAULT TARGET
# ================================
FROM runtime AS default
