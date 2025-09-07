@echo off
echo 🛑 Stopping AI DevOps System...
echo ================================

REM Stop all services gracefully
echo 📊 Stopping all services...
docker-compose down

echo.
echo ✅ AI DevOps System stopped successfully

REM Show remaining containers (should be empty)
echo.
echo 📋 Remaining containers:
docker-compose ps

pause
