@echo off
REM Dev Agent Service Stop Script (Windows)

set SERVICE_NAME=dev-agent-service
set REDIS_NAME=dev-agent-redis

echo Stopping Dev Agent Service containers...

echo Stopping service container...
docker stop %SERVICE_NAME% 2>nul
docker rm %SERVICE_NAME% 2>nul

echo Stopping Redis container...
docker stop %REDIS_NAME% 2>nul
docker rm %REDIS_NAME% 2>nul

echo All containers stopped successfully!
