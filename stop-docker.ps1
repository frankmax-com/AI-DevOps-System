# AI DevOps System - Docker Stop Script for Windows

Write-Host "🛑 Stopping AI DevOps System..." -ForegroundColor Red
Write-Host "================================" -ForegroundColor Red

# Stop all services gracefully
Write-Host "📊 Stopping all services..." -ForegroundColor Yellow
docker-compose down

# Optional: Remove volumes (uncomment to reset all data)
# Write-Host "🗑️  Removing volumes..." -ForegroundColor Yellow
# docker-compose down -v

# Optional: Remove images (uncomment to free disk space)
# Write-Host "🗑️  Removing images..." -ForegroundColor Yellow
# docker-compose down --rmi all

Write-Host "✅ AI DevOps System stopped successfully" -ForegroundColor Green

# Show remaining containers (should be empty)
Write-Host ""
Write-Host "📋 Remaining containers:" -ForegroundColor Yellow
docker-compose ps
