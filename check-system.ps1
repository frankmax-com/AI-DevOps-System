# AI DevOps System - Pre-flight Check

Write-Host "🔍 AI DevOps System - Pre-flight Check" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan

$allGood = $true

# Check Docker installation
Write-Host "`n🐳 Checking Docker..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version
    Write-Host "✅ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
    $allGood = $false
}

# Check Docker daemon
if ($allGood) {
    Write-Host "`n🔄 Checking Docker daemon..." -ForegroundColor Yellow
    try {
        docker info | Out-Null
        Write-Host "✅ Docker daemon is running" -ForegroundColor Green
    } catch {
        Write-Host "❌ Docker daemon not running. Please start Docker Desktop." -ForegroundColor Red
        Write-Host "   💡 Start Docker Desktop and wait for it to be ready" -ForegroundColor Yellow
        $allGood = $false
    }
}

# Check Docker Compose
if ($allGood) {
    Write-Host "`n📦 Checking Docker Compose..." -ForegroundColor Yellow
    try {
        $composeVersion = docker-compose --version
        Write-Host "✅ Docker Compose available: $composeVersion" -ForegroundColor Green
    } catch {
        Write-Host "❌ Docker Compose not found." -ForegroundColor Red
        $allGood = $false
    }
}

# Check for required files
Write-Host "`n📁 Checking required files..." -ForegroundColor Yellow

$requiredFiles = @(
    "docker-compose.yml",
    "monitoring/prometheus.yml"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "❌ Missing: $file" -ForegroundColor Red
        $allGood = $false
    }
}

# Check environment files
Write-Host "`n🔧 Checking environment files..." -ForegroundColor Yellow

$services = @(
    "controller-service",
    "github-governance-factory",
    "azure-devops-governance-factory", 
    "ai-provider-factory",
    "database-governance-factory"
)

$envMissing = @()
foreach ($service in $services) {
    if (Test-Path "$service\.env") {
        Write-Host "✅ Found: $service\.env" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Missing: $service\.env" -ForegroundColor Yellow
        $envMissing += $service
    }
}

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan

if ($allGood) {
    Write-Host "🎉 Pre-flight check passed!" -ForegroundColor Green
    
    if ($envMissing.Count -gt 0) {
        Write-Host "`n⚠️  Environment files missing for:" -ForegroundColor Yellow
        foreach ($service in $envMissing) {
            Write-Host "   • $service" -ForegroundColor Yellow
        }
        Write-Host "`n💡 Run this to create them from examples:" -ForegroundColor Cyan
        Write-Host "   .\create-env-files.ps1" -ForegroundColor Green
        Write-Host "`n📖 See ENVIRONMENT-SETUP.md for configuration details" -ForegroundColor Cyan
    }
    
    Write-Host "`n🚀 Ready to start AI DevOps System!" -ForegroundColor Green
    Write-Host "   Run: .\quick-start.bat" -ForegroundColor Cyan
    
} else {
    Write-Host "❌ Pre-flight check failed!" -ForegroundColor Red
    Write-Host "`n🔧 Please fix the issues above before starting the system." -ForegroundColor Yellow
    
    if ((Get-Command docker -ErrorAction SilentlyContinue) -and !(docker info *>$null)) {
        Write-Host "`n💡 Most common issue: Docker Desktop not running" -ForegroundColor Cyan
        Write-Host "   1. Start Docker Desktop" -ForegroundColor White
        Write-Host "   2. Wait for 'Docker Desktop is running' notification" -ForegroundColor White
        Write-Host "   3. Run this script again" -ForegroundColor White
    }
}

Write-Host "`n📚 Documentation:" -ForegroundColor Yellow
Write-Host "   • Docker Setup: DOCKER-SETUP.md" -ForegroundColor White
Write-Host "   • Environment: ENVIRONMENT-SETUP.md" -ForegroundColor White
Write-Host "   • Main README: README.md" -ForegroundColor White
