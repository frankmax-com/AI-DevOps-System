@echo off
echo Starting AI Provider Agent Service...

REM Check if Docker is running
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

REM Create .env file if it doesn't exist
if not exist .env (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration before running again.
    pause
    exit /b 1
)

REM Build and start services
echo Building and starting services...
docker-compose up --build -d

REM Wait for services to be ready
echo Waiting for services to start...
timeout /t 10 /nobreak >nul

REM Check service health
echo Checking service health...
curl -f http://localhost:8080/health >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ AI Provider Agent Service is running on http://localhost:8080
) else (
    echo ✗ Service health check failed
)

curl -f http://localhost:9090 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Prometheus is running on http://localhost:9090
) else (
    echo ✗ Prometheus health check failed
)

curl -f http://localhost:3000 >nul 2>&1
if %errorlevel% equ 0 (
    echo ✓ Grafana is running on http://localhost:3000
) else (
    echo ✗ Grafana health check failed
)

echo.
echo Services started successfully!
echo.
echo Available endpoints:
echo   API: http://localhost:8080
echo   Health: http://localhost:8080/health
echo   Metrics: http://localhost:8080/metrics
echo   Prometheus: http://localhost:9090
echo   Grafana: http://localhost:3000 (admin/admin)
echo.
echo Press any key to continue...
pause >nul
