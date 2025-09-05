# Database Governance Factory - Production Dockerfile

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install test dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    pytest-asyncio==0.21.1 \
    pytest-cov==4.1.0 \
    pytest-benchmark==4.0.0 \
    pytest-mock==3.12.0 \
    faker==20.1.0 \
    responses==0.24.1

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY tests/ ./tests/
COPY test_system.py .
COPY main.py .

# Create necessary directories
RUN mkdir -p /app/logs /app/backups

# Create non-root user for security
RUN groupadd -r governance && useradd -r -g governance governance
RUN chown -R governance:governance /app
USER governance

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV GOVERNANCE_API_HOST=0.0.0.0
ENV GOVERNANCE_API_PORT=8080

# Start the application
CMD ["python", "main.py"]
