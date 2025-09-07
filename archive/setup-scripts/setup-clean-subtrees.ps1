# Clean Agent Service Subtree Setup
# This script sets up git subtrees for agent services without committing secrets

Write-Host "Setting up clean git subtrees for agent services..." -ForegroundColor Green

# List of services to convert to subtrees
$services = @(
    "dev-agent-service",
    "ai-provider-agent-service", 
    "qa-agent-service",
    "security-agent-service", 
    "release-agent-service",
    "pm-agent-service",
    "audit-service"
)

function Setup-CleanSubtree {
    param([string]$ServiceName)
    
    Write-Host "Setting up subtree for $ServiceName..." -ForegroundColor Cyan
    
    $repoUrl = "https://github.com/frankmax-com/$ServiceName.git"
    $tempDir = "..\temp-$ServiceName"
    
    try {
        # Create and setup temp directory
        if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Copy service files, excluding secrets
        Copy-Item -Recurse "$ServiceName\*" $tempDir -Exclude "*.env"
        
        # Ensure .env.example exists but remove any actual secrets
        $envExamplePath = Join-Path $tempDir ".env.example"
        if (Test-Path "$ServiceName\.env.example") {
            Copy-Item "$ServiceName\.env.example" $envExamplePath
        } elseif (Test-Path "$ServiceName\.env") {
            # Create sanitized .env.example from .env
            $envContent = Get-Content "$ServiceName\.env" | ForEach-Object {
                if ($_ -match "=.*") {
                    $key = ($_ -split "=")[0]
                    "$key=your_${key.ToLower()}_here"
                } else {
                    $_
                }
            }
            $envContent | Out-File -FilePath $envExamplePath -Encoding UTF8
        }
        
        # Initialize git repo
        Push-Location $tempDir
        git init
        git add .
        
        # Create clean commit message
        $commitMsg = @"
feat: initial $ServiceName setup

$ServiceName
$("=" * $ServiceName.Length)
AI DevOps service for automated workflows

- Part of the AI DevOps monorepo
- Stored as a git subtree  
- Communicates via async FastAPI APIs
- No secrets committed to repository
"@
        
        git commit -m $commitMsg
        git remote add origin $repoUrl
        
        # Push to remote repository
        git push -u origin master
        
        Pop-Location
        
        # Setup subtree in main repo
        git rm -r $ServiceName
        git commit -m "refactor: remove $ServiceName directory to prepare for subtree"
        git subtree add --prefix=$ServiceName $repoUrl master --squash
        
        Write-Host "✅ Successfully set up subtree for $ServiceName" -ForegroundColor Green
        
        # Clean up temp directory
        Remove-Item -Recurse -Force $tempDir
        
    }
    catch {
        Write-Host "❌ Failed to set up subtree for $ServiceName`: $($_.Exception.Message)" -ForegroundColor Red
        if (Test-Path $tempDir) { Remove-Item -Recurse -Force $tempDir }
        Pop-Location -ErrorAction SilentlyContinue
    }
}

# Process each service
foreach ($service in $services) {
    if (Test-Path $service) {
        Setup-CleanSubtree -ServiceName $service
        Write-Host ""
    } else {
        Write-Host "⚠ Service directory $service not found, skipping..." -ForegroundColor Yellow
    }
}

Write-Host "Agent service subtree setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Verify subtrees with:" -ForegroundColor Yellow
Write-Host "git log --oneline --grep='subtree'" -ForegroundColor Gray
