# Quick Start Script for AI DevOps Controller Service

Write-Host "🚀 AI DevOps Controller Service - Development Setup" -ForegroundColor Green
Write-Host "=" * 60

# Check Python version
Write-Host "`n📋 Checking Prerequisites..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Python: $pythonVersion" -ForegroundColor Green
} else {
    Write-Host "❌ Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check if virtual environment exists
if (-not (Test-Path ".venv")) {
    Write-Host "`n🔧 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "`n🔌 Activating virtual environment..." -ForegroundColor Yellow
& ".venv\Scripts\Activate.ps1"
Write-Host "✅ Virtual environment activated" -ForegroundColor Green

# Install Controller Service dependencies
Write-Host "`n📦 Installing Controller Service dependencies..." -ForegroundColor Yellow
Set-Location controller-service
pip install -r requirements.txt
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    exit 1
}

# Create .env file if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "`n⚙️  Creating environment configuration..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "✅ Environment file created (.env)" -ForegroundColor Green
    Write-Host "💡 Edit .env file with your Azure Key Vault credentials" -ForegroundColor Cyan
}

# Check if Docker is running (for agent spawning)
Write-Host "`n🐳 Checking Docker status..." -ForegroundColor Yellow
try {
    docker ps | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
    $dockerRunning = $true
} catch {
    Write-Host "⚠️  Docker not running - Agent spawning will be disabled" -ForegroundColor Yellow
    $dockerRunning = $false
}

# Start governance factories check
Write-Host "`n🏭 Checking Governance Factories..." -ForegroundColor Yellow
$factories = @(
    @{Name="GitHub"; Port=8001},
    @{Name="Azure DevOps"; Port=8002}, 
    @{Name="AI Provider"; Port=8003},
    @{Name="Database"; Port=8004}
)

foreach ($factory in $factories) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($factory.Port)/health" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "✅ $($factory.Name) Governance Factory (port $($factory.Port))" -ForegroundColor Green
    } catch {
        Write-Host "⚠️  $($factory.Name) Governance Factory not running (port $($factory.Port))" -ForegroundColor Yellow
    }
}

Write-Host "`n🎯 Setup Complete!" -ForegroundColor Green
Write-Host "=" * 60

Write-Host "`n📋 Next Steps:" -ForegroundColor Cyan
Write-Host "1. Edit controller-service/.env with your Azure credentials"
Write-Host "2. Start Docker Desktop (for agent spawning)"
Write-Host "3. Start governance factories:"
Write-Host "   - cd github-governance-factory && docker-compose up -d"
Write-Host "   - cd azure-devops-governance-factory && docker-compose up -d"
Write-Host "   - cd ai-provider-factory && docker-compose up -d"
Write-Host "   - cd database-governance-factory && docker-compose up -d"
Write-Host "4. Run Controller Service:"
Write-Host "   - cd controller-service"
Write-Host "   - python src/main.py"
Write-Host "5. Access API documentation: http://localhost:8000/docs"

Write-Host "`n🚀 Ready to build AI Agent Startup Creation Platform!" -ForegroundColor Green
