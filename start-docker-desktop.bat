@echo off
echo 🐳 Starting Docker Desktop...
echo =============================

REM Try to start Docker Desktop
echo 📱 Opening Docker Desktop...
start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"

if errorlevel 1 (
    echo.
    echo ❌ Could not auto-start Docker Desktop
    echo 💡 Please manually start Docker Desktop from:
    echo    - Windows Start Menu
    echo    - Desktop shortcut
    echo    - System tray
) else (
    echo ✅ Docker Desktop is starting...
    echo.
    echo ⏳ Please wait for Docker Desktop to be ready
    echo    Look for "Docker Desktop is running" notification
    echo.
    echo 🚀 Once ready, run: quick-start.bat
)

echo.
pause
