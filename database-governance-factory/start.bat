@echo off

REM Database Governance Factory - Quick Start Script for Windows
REM This script helps you get the Database Governance Factory up and running quickly

echo 🚀 Database Governance Factory - Quick Start
echo ==============================================

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not running. Please start Docker and try again.
    exit /b 1
)

REM Check if Docker Compose is available
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not available. Please install Docker Compose and try again.
    exit /b 1
)

REM Create .env file from example if it doesn't exist
if not exist .env (
    echo 📝 Creating .env file from .env.example...
    copy .env.example .env
    echo ✅ Created .env file. Please review and update it with your actual credentials.
)

REM Create necessary directories
echo 📁 Creating necessary directories...
if not exist logs mkdir logs
if not exist backups mkdir backups
if not exist monitoring\grafana\dashboards mkdir monitoring\grafana\dashboards
if not exist nginx\sites-enabled mkdir nginx\sites-enabled
if not exist ssl mkdir ssl

REM Pull latest images
echo 📥 Pulling latest Docker images...
docker-compose pull

REM Start the infrastructure services first
echo 🏗️  Starting infrastructure services...
docker-compose up -d governance-mongodb governance-postgresql governance-redis

REM Wait for databases to be ready
echo ⏳ Waiting for databases to be ready...
timeout /t 30 /nobreak >nul

REM Start monitoring services
echo 📊 Starting monitoring services...
docker-compose up -d governance-prometheus governance-grafana governance-jaeger

REM Start the main application
echo 🎯 Starting Database Governance Factory...
docker-compose up -d governance-api

REM Start additional services
echo 🔧 Starting additional services...
docker-compose up -d governance-nginx governance-backup

REM Show service status
echo 📋 Service Status:
docker-compose ps

echo.
echo 🎉 Database Governance Factory is starting up!
echo.
echo 📍 Service URLs:
echo    • Governance API:     http://localhost:8080
echo    • API Documentation:  http://localhost:8080/docs
echo    • Grafana Dashboard:  http://localhost:3000 (admin/governance-grafana-pass)
echo    • Prometheus:         http://localhost:9090
echo    • Jaeger Tracing:     http://localhost:16686
echo    • Kibana:             http://localhost:5601
echo.
echo 🔧 Database Connections:
echo    • MongoDB:    localhost:27017 (admin/governance-admin-pass)
echo    • PostgreSQL: localhost:5432 (postgres/governance-postgres-pass)
echo    • Redis:      localhost:6379 (governance-redis-pass)
echo.
echo 📝 Next Steps:
echo    1. Wait 2-3 minutes for all services to fully start
echo    2. Visit http://localhost:8080/health to check API health
echo    3. Visit http://localhost:8080/docs to explore the API
echo    4. Configure your databases in the .env file
echo    5. Register your databases via the API
echo.
echo 🛑 To stop all services: docker-compose down
echo 🔄 To restart services: docker-compose restart
echo 📊 To view logs: docker-compose logs -f [service-name]

REM Optional: Open browser to API documentation
timeout /t 5 /nobreak >nul
start http://localhost:8080/docs

echo.
echo ✅ Database Governance Factory startup complete!
pause
