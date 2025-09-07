@echo off
echo 🐳 AI DevOps System - Quick Docker Launch
echo ========================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)

echo ✅ Docker is running

REM Launch the PowerShell script with proper execution policy
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start-docker.ps1"

echo.
echo 🎉 Launch complete! Check the output above for service URLs.
pause
