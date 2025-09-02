@echo off
echo Testing AI Provider Agent Service...

REM Check if service is running
curl -f http://localhost:8080/health >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Service is not running. Please start it first with start.bat
    pause
    exit /b 1
)

echo ✓ Service is running

REM Test health endpoint
echo Testing health endpoint...
curl -s http://localhost:8080/health
echo.

REM Test provider status
echo Testing provider status...
curl -s http://localhost:8080/providers/status
echo.

REM Test AI processing (simple request)
echo Testing AI processing...
curl -s -X POST http://localhost:8080/ai/process ^
     -H "Content-Type: application/json" ^
     -d "{\"task_type\":\"thinking\",\"prompt\":\"Hello, how are you?\",\"max_tokens\":50}"
echo.

echo Testing completed!
pause
