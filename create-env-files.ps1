# Create Environment Files from Examples

Write-Host "🔧 Creating Environment Files from Examples" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$services = @(
    "controller-service",
    "github-governance-factory",
    "azure-devops-governance-factory",
    "ai-provider-factory", 
    "database-governance-factory"
)

$created = @()
$skipped = @()
$missing = @()

foreach ($service in $services) {
    Write-Host "`n📁 Processing $service..." -ForegroundColor Yellow
    
    $exampleFile = "$service\.env.example"
    $envFile = "$service\.env"
    
    if (Test-Path $exampleFile) {
        if (!(Test-Path $envFile)) {
            Copy-Item $exampleFile $envFile
            Write-Host "✅ Created $envFile" -ForegroundColor Green
            $created += $service
        } else {
            Write-Host "⚠️  $envFile already exists (skipped)" -ForegroundColor Yellow
            $skipped += $service
        }
    } else {
        Write-Host "❌ $exampleFile not found" -ForegroundColor Red
        $missing += $service
    }
}

# Summary
Write-Host "`n" + "="*50 -ForegroundColor Cyan
Write-Host "📊 Summary" -ForegroundColor Cyan

if ($created.Count -gt 0) {
    Write-Host "`n✅ Created environment files for:" -ForegroundColor Green
    foreach ($service in $created) {
        Write-Host "   • $service" -ForegroundColor Green
    }
}

if ($skipped.Count -gt 0) {
    Write-Host "`n⚠️  Skipped (already exist):" -ForegroundColor Yellow
    foreach ($service in $skipped) {
        Write-Host "   • $service" -ForegroundColor Yellow
    }
}

if ($missing.Count -gt 0) {
    Write-Host "`n❌ Missing example files:" -ForegroundColor Red
    foreach ($service in $missing) {
        Write-Host "   • $service" -ForegroundColor Red
    }
}

# Next steps
Write-Host "`n🔧 Next Steps:" -ForegroundColor Cyan

if ($created.Count -gt 0 -or $skipped.Count -gt 0) {
    Write-Host "1. Edit environment files with your API keys and credentials:" -ForegroundColor White
    
    foreach ($service in ($created + $skipped)) {
        Write-Host "   notepad $service\.env" -ForegroundColor Gray
    }
    
    Write-Host "`n2. See ENVIRONMENT-SETUP.md for detailed configuration guide" -ForegroundColor White
    Write-Host "3. Run .\check-system.ps1 to verify setup" -ForegroundColor White
    Write-Host "4. Start the system with .\quick-start.bat" -ForegroundColor White
} else {
    Write-Host "❌ No environment files created. Check if service directories exist." -ForegroundColor Red
}

Write-Host "`n📚 Documentation:" -ForegroundColor Yellow
Write-Host "   • Environment Setup: ENVIRONMENT-SETUP.md" -ForegroundColor White
Write-Host "   • Docker Setup: DOCKER-SETUP.md" -ForegroundColor White
