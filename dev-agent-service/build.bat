@echo off
REM Dev Agent Service Build Script (Windows)

set SERVICE_NAME=dev-agent-service
set DOCKER_IMAGE=%SERVICE_NAME%:latest
set DOCKERFILE=Dockerfile
set ENV_FILE=.env

echo Building Docker image %DOCKER_IMAGE%...

REM Check if .env file exists
if not exist "%ENV_FILE%" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Please edit .env file with your configuration.
) else (
    docker build -t %DOCKER_IMAGE% -f %DOCKERFILE% .
)

echo Build complete!
