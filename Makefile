# Orchestrator Service Makefile (Linux/macOS)

.PHONY: help build run build-redis run-redis stop stop-redis logs test bootstrap clean validate-pat deploy status

# Configuration
SERVICE_NAME=orchestrator-service
REDIS_NAME=orchestrator-redis
DOCKER_IMAGE=$(SERVICE_NAME):latest
DOCKERFILE=Dockerfile
COMPOSE_FILE=docker-compose.yml

# Environment file
ENV_FILE=.env

# Default help target
help:
	@echo "Available targets:"
	@echo "  build          - Build orchestrator Docker image"
	@echo "  run           - Run orchestrator service + Redis"
	@echo "  stop          - Stop orchestrator service + Redis"
	@echo "  logs          - Tail orchestrator logs"
	@echo "  test          - Run tests in Docker container"
	@echo "  bootstrap     - Bootstrap Azure DevOps project"
	@echo "  deploy        - Deploy all services (docker-compose)"
	@echo "  validate-pat  - Validate Azure DevOps PAT permissions"
	@echo "  status        - Show service status"
	@echo "  clean         - Remove containers and images"
	@echo ""
	@echo "Environment: Ensure .env file exists with required variables"

# Build Docker image
build:
	@echo "Building Docker image $(DOCKER_IMAGE)..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Creating .env file from template..."; \
		cp .env.example .env; \
		echo "Please edit .env file with your configuration."; \
		exit 1; \
	fi
	@docker build -t $(DOCKER_IMAGE) -f $(DOCKERFILE) .

# Start Redis container
run-redis:
	@echo "Starting Redis container..."
	@docker run -d --name $(REDIS_NAME) \
		-p 6379:6379 \
		--restart unless-stopped \
		redis:alpine || echo "Redis container already running"

# Start orchestrator container
run-service:
	@echo "Starting orchestrator service container..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: .env file not found. Please copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@docker run -d --name $(SERVICE_NAME) \
		--link $(REDIS_NAME) \
		-p 8000:8000 \
		--env-file .env \
		--restart unless-stopped \
		$(DOCKER_IMAGE)
	@echo "Orchestrator service available at http://localhost:8000"
	@echo "Health check: http://localhost:8000/healthz"

# Run both containers
run: run-redis
	@sleep 2
	@$(MAKE) run-service

# Stop orchestrator container
stop-service:
	@echo "Stopping orchestrator service container..."
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

# Show orchestrator logs
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
		-v "$(PWD)/tests:/app/tests" \
		-v "$(PWD)/src:/app/src" \
		-w /app \
		$(DOCKER_IMAGE) \
		python -m pytest $(ARGS) -v --cov=src --cov-report=term-missing

# Bootstrap Azure DevOps project
bootstrap:
	@echo "Bootstrapping Azure DevOps project..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: .env file not found. Please copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@docker run --rm \
		--env-file .env \
		--network host \
		$(DOCKER_IMAGE) \
		curl -X POST http://localhost:8000/bootstrap -d '{}' -H "Content-Type: application/json"
	@echo "Bootstrap request sent. Check logs for progress."

# Deploy all services (local development only)
deploy:
	@echo "Deploying all services with docker-compose..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: .env file not found. Please copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@docker-compose -f $(COMPOSE_FILE) up -d --build

# Stop all services
stop-all:
	@echo "Stopping all services..."
	@docker-compose -f $(COMPOSE_FILE) down

# Validate Azure DevOps PAT permissions
validate-pat:
	@echo "Validating Azure DevOps PAT permissions..."
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "Error: .env file not found."; \
		exit 1; \
	fi
	@echo "Checking PAT permissions for orchestrator..."
	@docker run --rm \
		--env-file .env \
		--network host \
		$(DOCKER_IMAGE) \
		curl -f http://localhost:8000/healthz >/dev/null 2>&1 && echo "✓ PAT valid" || echo "✗ PAT validation failed"

# Clean up containers and images
clean:
	@echo "Cleaning up containers and images..."
	@docker stop $(SERVICE_NAME) $(REDIS_NAME) || true
	@docker rm $(SERVICE_NAME) $(REDIS_NAME) || true
	@docker rmi $(DOCKER_IMAGE) || true
	@docker-compose -f $(COMPOSE_FILE) down -v --remove-orphans || true
	@docker system prune -f

# Show container status
status:
	@echo "=== Orchestrator Service Status ==="
	@docker ps --filter name=$(SERVICE_NAME) --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@docker ps --filter name=$(REDIS_NAME) --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
	@echo ""
	@echo "=== Environment Check ==="
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "✓ .env file exists"; \
	else \
		echo "⚠  .env file missing"; \
	fi

# Health check
health:
	@docker exec $(SERVICE_NAME) curl -f http://localhost:8000/healthz >/dev/null 2>&1 && \
	echo "✓ Orchestrator service is healthy" || echo "✗ Orchestrator service health check failed"

# Open shell in running container
shell:
	@docker exec -it $(SERVICE_NAME) /bin/bash

# Show available endpoints
api:
	@echo "=== Orchestrator Service API Endpoints ==="
	@echo "Health Check:  http://localhost:8000/healthz"
	@echo "Metrics:       http://localhost:8000/metrics"
	@echo "Webhook:       http://localhost:8000/webhooks/azure-devops"
	@echo "Project Status: http://localhost:8000/projects/{project}/status"
	@echo "Bootstrap:     http://localhost:8000/bootstrap (POST)"
	@echo ""
	@echo "Start service: make run"
	@echo "View logs:     make logs"
	@echo "Bootstrap:     make bootstrap"
