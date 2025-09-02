@echo off
REM Dev Agent Service Test Script (Windows)

set SERVICE_NAME=dev-agent-service
set REDIS_NAME=dev-agent-redis
set DOCKER_IMAGE=%SERVICE_NAME%:latest
set ENV_FILE=.env

echo Running tests in Docker container...

REM Check if .env file exists
if not exist "%ENV_FILE%" (
    echo Warning: .env file not found, some tests may fail.
    echo Copy .env.example to .env and configure for full functionality.
)

REM Create a temporary test container
docker run --rm ^
    --link %REDIS_NAME% ^
    --env-file %ENV_FILE% ^
    -v "%cd%/tests:/app/tests" ^
    -v "%cd%/src:/app/src" ^
    -w /app ^
    %DOCKER_IMAGE% ^
    python -m pytest %*
