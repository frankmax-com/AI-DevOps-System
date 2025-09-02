@echo off
echo Stopping AI Provider Agent Service...

REM Stop all services
docker-compose down

REM Optional: Remove volumes (uncomment if you want to reset data)
REM docker-compose down -v

echo Services stopped successfully!
pause
