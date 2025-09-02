# Dev Agent Service Makefile (Linux/macOS)

.PHONY: help build run run-redis stop stop-redis logs test clean

# Configuration
SERVICE_NAME=dev-agent-service
REDIS_NAME=dev-agent-redis
DOCKER_IMAGE=$(SERVICE_NAME):latest
DOCKERFILE=Dockerfile

# Environment file
ENV_FILE=.env

# Default help target
help:
	@echo "Available targets:"
	@echo "  build     - Build Docker image"
	@echo "  run       - Run service and Redis containers"
	@echo "  stop      - Stop service and Redis containers"
	@echo "  logs      - Show service container logs"
	@echo "  test      - Run tests in Docker container"
	@echo "  clean     - Remove containers and images"
	@echo ""
	@echo "Environment: Ensure .env file exists with required variables"

# Build Docker image
build:
	@echo "Building Docker image $(DOCKER_IMAGE)..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "Please edit .env file with your configuration."; \
	else \
		docker build -t $(DOCKER_IMAGE) -f $(DOCKERFILE) .; \
	fi

# Run Redis container
run-redis:
	@echo "Starting Redis container..."
	@docker run -d --name $(REDIS_NAME) \
		-p 6379:6379 \
		--restart unless-stopped \
		redis:alpine || true

# Run service container
run-service:
	@echo "Starting service container..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: .env file not found. Please copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@docker run -d --name $(SERVICE_NAME) \
		--link $(REDIS_NAME) \
		-p 8080:8080 \
		--env-file .env \
		--restart unless-stopped \
		$(DOCKER_IMAGE)
	@echo "Service available at http://localhost:8080"
	@echo "Health check: http://localhost:8080/healthz"

# Run both containers
run: run-redis
	@sleep 2
	@$(MAKE) run-service

# Stop service container
stop-service:
	@echo "Stopping service container..."
	@docker stop $(SERVICE_NAME) || true
	@docker rm $(SERVICE_NAME) || true

# Stop Redis container
stop-redis:
	@echo "Stopping Redis container..."
	@docker stop $(REDIS_NAME) || true
	@docker rm $(REDIS_NAME) || true

# Stop all containers
stop: stop-service
	@$(MAKE) stop-redis

# Show logs
logs:
	@docker logs -f $(SERVICE_NAME)

# Show Redis logs
logs-redis:
	@docker logs -f $(REDIS_NAME)

# Run tests in Docker container
test:
	@echo "Running tests in Docker container..."
	@docker run --rm \
		--link $(REDIS_NAME) \
		--env-file .env \
		-v $(PWD)/tests:/app/tests \
		-v $(PWD)/src:/app/src \
		-w /app \
		$(DOCKER_IMAGE) \
		python -m pytest $(ARGS) -v

# Run tests with coverage
test-coverage:
	@$(MAKE) test ARGS="--cov=src --cov-report=html"

# Clean up containers and images
clean:
	@echo "Cleaning up containers and images..."
	@docker stop $(SERVICE_NAME) $(REDIS_NAME) || true
	@docker rm $(SERVICE_NAME) $(REDIS_NAME) || true
	@docker rmi $(DOCKER_IMAGE) || true
	@docker system prune -f

# Show container status
status:
	@echo "=== Container Status ==="
	@docker ps --filter name=$(SERVICE_NAME) --filter name=$(REDIS_NAME)
	@echo ""
	@echo "=== Environment Check ==="
	@if [ -f "$(ENV_FILE)" ]; then \
		echo ".env file exists"; \
	else \
		echo "Warning: .env file missing"; \
	fi

# Open shell in running container
shell:
	@docker exec -it $(SERVICE_NAME) /bin/bash

# Health check
health:
	@docker exec $(SERVICE_NAME) python -c "import requests; requests.get('http://localhost:8080/healthz', timeout=5)" && \
	echo "Service is healthy" || echo "Service health check failed"
