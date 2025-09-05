@echo off
REM Docker-based test runner for Database Governance Factory
REM This script runs all tests in containerized environment

echo ===================================
echo Database Governance Factory Tests
echo ===================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not available in PATH
    echo Please install Python or add it to your PATH
    pause
    exit /b 1
)

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not available in PATH
    echo Please install Docker Desktop and ensure it's running
    pause
    exit /b 1
)

REM Check if Docker Compose is available
docker compose version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Compose is not available
    echo Please update Docker Desktop to get Docker Compose
    pause
    exit /b 1
)

echo Docker environment verified successfully
echo.

REM Parse command line arguments
if "%1"=="" (
    echo Running comprehensive test suite...
    python run_docker_tests.py
) else (
    echo Running %1 tests...
    python run_docker_tests.py %1
)

REM Check exit code
if errorlevel 1 (
    echo.
    echo ===================================
    echo TEST EXECUTION FAILED
    echo ===================================
    echo Check the logs above for details
    pause
    exit /b 1
) else (
    echo.
    echo ===================================
    echo TEST EXECUTION SUCCESSFUL
    echo ===================================
    echo All tests passed successfully!
)

pause
