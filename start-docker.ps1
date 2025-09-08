<#
    AI DevOps System - Docker Startup Script for Windows
    Note: This script intentionally uses only ASCII in output to avoid
    encoding issues on some PowerShell consoles.
#>

Write-Host "AI DevOps System - Docker Environment Setup" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "Docker is running" -ForegroundColor Green
} catch {
    Write-Host "Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if docker-compose is available
if (!(Get-Command docker-compose -ErrorAction SilentlyContinue)) {
    Write-Host "docker-compose not found. Please install Docker Compose." -ForegroundColor Red
    exit 1
}

Write-Host "Docker Compose is available" -ForegroundColor Green

# Create environment files if they don't exist
Write-Host "`nSetting up environment files..." -ForegroundColor Yellow

# Controller Service
if (!(Test-Path "controller-service\.env")) {
    if (Test-Path "controller-service\.env.example") {
        Copy-Item "controller-service\.env.example" "controller-service\.env"
        Write-Host "Created controller-service\.env" -ForegroundColor Green
        Write-Host "Edit controller-service\.env with your Azure Key Vault credentials" -ForegroundColor Yellow
    } else {
        Write-Host "controller-service\.env.example not found" -ForegroundColor Yellow
    }
} else {
    Write-Host "controller-service\.env exists" -ForegroundColor Green
}

# GitHub Governance Factory
if (!(Test-Path "github-governance-factory\.env")) {
    if (Test-Path "github-governance-factory\.env.example") {
        Copy-Item "github-governance-factory\.env.example" "github-governance-factory\.env"
    Write-Host "Created github-governance-factory\.env" -ForegroundColor Green
    } else {
    Write-Host "github-governance-factory\.env.example not found" -ForegroundColor Yellow
    }
}

# Azure DevOps Governance Factory
if (!(Test-Path "azure-devops-governance-factory\.env")) {
    if (Test-Path "azure-devops-governance-factory\.env.example") {
        Copy-Item "azure-devops-governance-factory\.env.example" "azure-devops-governance-factory\.env"
    Write-Host "Created azure-devops-governance-factory\.env" -ForegroundColor Green
    } else {
    Write-Host "azure-devops-governance-factory\.env.example not found" -ForegroundColor Yellow
    }
}

# AI Provider Factory
if (!(Test-Path "ai-provider-factory\.env")) {
    if (Test-Path "ai-provider-factory\.env.example") {
        Copy-Item "ai-provider-factory\.env.example" "ai-provider-factory\.env"
    Write-Host "Created ai-provider-factory\.env" -ForegroundColor Green
    } else {
    Write-Host "ai-provider-factory\.env.example not found" -ForegroundColor Yellow
    }
}

# Database Governance Factory
if (!(Test-Path "database-governance-factory\.env")) {
    if (Test-Path "database-governance-factory\.env.example") {
        Copy-Item "database-governance-factory\.env.example" "database-governance-factory\.env"
    Write-Host "Created database-governance-factory\.env" -ForegroundColor Green
    } else {
    Write-Host "database-governance-factory\.env.example not found" -ForegroundColor Yellow
    }
}

# Create monitoring directory if it doesn't exist
if (!(Test-Path "monitoring")) {
    New-Item -ItemType Directory -Path "monitoring" | Out-Null
    Write-Host "Created monitoring directory" -ForegroundColor Green
}

# Start services in order
Write-Host "`nStarting AI DevOps System..." -ForegroundColor Yellow

# Step 1: Start core infrastructure
Write-Host "`nStarting core infrastructure (Redis, PostgreSQL, MongoDB)..." -ForegroundColor Yellow
docker-compose up -d redis postgres mongo

# Wait for databases to be ready
Write-Host "Waiting for databases to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Step 2: Start governance factories
Write-Host "`nStarting governance factories..." -ForegroundColor Yellow
docker-compose up -d github-governance azure-governance ai-provider database-governance

# Wait for governance factories to be ready
Write-Host "Waiting for governance factories to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

# Step 3: Start controller service
Write-Host "`nStarting Controller Service..." -ForegroundColor Yellow
docker-compose up -d controller-service

# Step 4: Start monitoring
Write-Host "`nStarting monitoring (Prometheus, Grafana)..." -ForegroundColor Yellow
docker-compose up -d prometheus grafana

# Wait for all services to be ready
Write-Host "`nWaiting for all services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 20

# Check service health
Write-Host "`nChecking service health..." -ForegroundColor Yellow

$services = @(
    @{Name="Controller Service"; Port=8000},
    @{Name="GitHub Governance"; Port=8001},
    @{Name="Azure Governance"; Port=8002},
    @{Name="AI Provider"; Port=8003},
    @{Name="Database Governance"; Port=8004}
)

$allHealthy = $true

foreach ($service in $services) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$($service.Port)/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "$($service.Name) (port $($service.Port)) - Healthy" -ForegroundColor Green
        } else {
            Write-Host "$($service.Name) (port $($service.Port)) - Not responding" -ForegroundColor Red
            $allHealthy = $false
        }
    } catch {
        Write-Host "$($service.Name) (port $($service.Port)) - Not responding" -ForegroundColor Red
        $allHealthy = $false
    }
}

# Show final status
Write-Host "`n================================================" -ForegroundColor Cyan
if ($allHealthy) {
    Write-Host "AI DevOps System is ready!" -ForegroundColor Green
} else {
    Write-Host "Some services may still be starting up..." -ForegroundColor Yellow
}

Write-Host "`nService URLs:" -ForegroundColor Yellow
Write-Host "- Controller Service API: " -NoNewline; Write-Host "http://localhost:8000/docs" -ForegroundColor Green
Write-Host "- GitHub Governance API: " -NoNewline; Write-Host "http://localhost:8001/docs" -ForegroundColor Green
Write-Host "- Azure Governance API: " -NoNewline; Write-Host "http://localhost:8002/docs" -ForegroundColor Green
Write-Host "- AI Provider API: " -NoNewline; Write-Host "http://localhost:8003/docs" -ForegroundColor Green
Write-Host "- Database Governance API: " -NoNewline; Write-Host "http://localhost:8004/docs" -ForegroundColor Green
Write-Host "- Prometheus: " -NoNewline; Write-Host "http://localhost:9091" -ForegroundColor Green
Write-Host "- Grafana: " -NoNewline; Write-Host "http://localhost:3001" -ForegroundColor Green -NoNewline; Write-Host " (admin/admin)" -ForegroundColor Cyan

Write-Host "`nManagement Commands:" -ForegroundColor Yellow
Write-Host "- View logs: " -NoNewline; Write-Host "docker-compose logs -f" -ForegroundColor Green
Write-Host "- Stop all: " -NoNewline; Write-Host "docker-compose down" -ForegroundColor Green
Write-Host "- Restart service: " -NoNewline; Write-Host "docker-compose restart SERVICE_NAME" -ForegroundColor Green
Write-Host "- Check status: " -NoNewline; Write-Host "docker-compose ps" -ForegroundColor Green

Write-Host "`nStartup routine complete." -ForegroundColor Green
