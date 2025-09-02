@echo off
REM Dev Agent Service Logs Script (Windows)

set SERVICE_NAME=dev-agent-service

echo Dev Agent Service Logs (press Ctrl+C to stop)...

docker logs -f %SERVICE_NAME%
