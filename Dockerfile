FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/

# Create logs directory
RUN mkdir -p /app/logs

# Set environment variables
ENV PYTHONPATH=/app
ENV AI_PROVIDER_CONFIG_PATH=/app/config/ai_providers_config.json
ENV LOG_LEVEL=INFO
ENV PORT=8080

# Create non-root user
RUN useradd -m -u 1000 aiagent && chown -R aiagent:aiagent /app
USER aiagent

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE ${PORT}

# Run the application
CMD ["python", "-m", "uvicorn", "src.ai_provider_agent:app", "--host", "0.0.0.0", "--port", "8080"]
