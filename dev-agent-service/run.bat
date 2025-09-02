@echo off
REM Dev Agent Service Run Script (Windows)

set SERVICE_NAME=dev-agent-service
set REDIS_NAME=dev-agent-redis
set DOCKER_IMAGE=%SERVICE_NAME%:latest
set ENV_FILE=.env

echo Starting Dev Agent Service and Redis...

REM Check if .env file exists
if not exist "%ENV_FILE%" (
    echo Error: .env file not found. Please copy .env.example to .env and configure it.
    exit /b 1
)

echo Starting Redis container...
docker run -d --name %REDIS_NAME% ^
    -p 6379:6379 ^
    --restart unless-stopped ^
    redis:alpine ^2>nul || echo Redis container already running or failed to start

timeout /t 3 /nobreak > nul

echo Starting service container...
docker run -d --name %SERVICE_NAME% ^
    --link %REDIS_NAME% ^
    -p 8080:8080 ^
    --env-file %ENV_FILE% ^
    --restart unless-stopped ^
    %DOCKER_IMAGE%

if %errorlevel% equ 0 (
    echo.
    echo Dev Agent Service started successfully!
    echo Service available at: http://localhost:8080
    echo Health check: http://localhost:8080/healthz
    echo.
    echo To view logs: logs.bat
    echo To stop: stop.bat
) else (
    echo Failed to start service container
)
