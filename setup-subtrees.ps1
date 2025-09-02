# AI DevOps Monorepo Setup Script (PowerShell)
# This script sets up the proper git subtree structure for agent services

Write-Host "Setting up AI DevOps monorepo with git subtrees..." -ForegroundColor Green

# Define services and their descriptions
$services = @{
    "orchestrator-service" = "AI coordination layer"
    "dev-agent-service" = "Code generation and scaffolding"
    "qa-agent-service" = "Testing automation"
    "security-agent-service" = "Vulnerability scanning"
    "release-agent-service" = "Deployment automation"
    "pm-agent-service" = "Requirements and planning"
    "audit-service" = "Audit trails and compliance"
    "ai-provider-agent-service" = "AI routing and provider integration"
}

# First, let's create all the GitHub repositories
Write-Host "Creating GitHub repositories..." -ForegroundColor Yellow
foreach ($service in $services.Keys) {
    $description = $services[$service]
    Write-Host "Creating repository for $service..." -ForegroundColor Cyan
    
    try {
        gh repo create "frankmax-com/$service" --public --description "AI DevOps $description"
        Write-Host "✓ Created repository frankmax-com/$service" -ForegroundColor Green
    }
    catch {
        Write-Host "Repository frankmax-com/$service may already exist" -ForegroundColor Yellow
    }
}

Write-Host "`nSetting up subtrees..." -ForegroundColor Yellow

# Function to setup subtree for a service
function Setup-Subtree {
    param(
        [string]$ServiceName,
        [string]$ServiceDesc
    )
    
    $repoUrl = "https://github.com/frankmax-com/$ServiceName.git"
    
    Write-Host "Setting up subtree for $ServiceName..." -ForegroundColor Cyan
    
    # Check if service directory exists and has content
    if (Test-Path $ServiceName) {
        Write-Host "Found existing $ServiceName directory"
        
        # Create a temporary git repo for this service
        $tempDir = "..\temp-$ServiceName"
        if (Test-Path $tempDir) {
            Remove-Item -Recurse -Force $tempDir
        }
        New-Item -ItemType Directory -Path $tempDir | Out-Null
        
        # Copy existing content to temp directory
        Copy-Item -Recurse "$ServiceName\*" $tempDir
        
        # Initialize git in temp directory
        Push-Location $tempDir
        git init
        git add .
        git commit -m "feat: initial $ServiceName setup from monorepo`n`n- Existing service structure`n- Ready for subtree integration"
        
        git remote add origin $repoUrl
        
        # Try to push to the remote repository
        try {
            git push -u origin master
            Write-Host "✓ Pushed $ServiceName to remote repository" -ForegroundColor Green
        }
        catch {
            Write-Host "⚠ Could not push to $ServiceName repository (may need to be created first)" -ForegroundColor Yellow
        }
        
        Pop-Location
        
        # Remove temp directory
        Remove-Item -Recurse -Force $tempDir
        
        # Now set up the subtree in the main repo
        # First remove the existing directory from git tracking
        git rm -r $ServiceName
        
        # Add as subtree
        try {
            git subtree add --prefix=$ServiceName $repoUrl master --squash
            Write-Host "✓ Set up subtree for $ServiceName" -ForegroundColor Green
        }
        catch {
            Write-Host "⚠ Could not set up subtree for $ServiceName (repository may be empty)" -ForegroundColor Yellow
        }
    }
    else {
        Write-Host "No existing directory found for $ServiceName, will create basic structure"
        
        # Create basic service structure
        New-Item -ItemType Directory -Path "$ServiceName\src" -Force | Out-Null
        New-Item -ItemType Directory -Path "$ServiceName\tests" -Force | Out-Null
        New-Item -ItemType Directory -Path "$ServiceName\specs\business" -Force | Out-Null
        New-Item -ItemType Directory -Path "$ServiceName\specs\functional" -Force | Out-Null
        New-Item -ItemType Directory -Path "$ServiceName\specs\implementation" -Force | Out-Null
        
        # Create README.md
        $readmeContent = @"
# $ServiceName

$ServiceDesc

## Purpose
This service is part of the AI DevOps platform and handles specific functionality as described below.

## Architecture
- FastAPI for HTTP endpoints
- Async/await for non-blocking operations
- Pydantic models for data validation
- Docker containerization

## Usage
This service communicates with the Orchestrator Service and other agent services through standardized HTTP APIs.

---
*This service is maintained as a git subtree in the main AI DevOps monorepo.*
"@
        $readmeContent | Out-File -FilePath "$ServiceName\README.md" -Encoding UTF8
        
        # Create requirements.txt
        $requirementsContent = @"
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
httpx==0.25.2
python-dotenv==1.0.0
structlog==23.2.0
"@
        $requirementsContent | Out-File -FilePath "$ServiceName\requirements.txt" -Encoding UTF8
        
        # Create __init__.py
        $initContent = @"
"""
$ServiceName
$("=" * $ServiceName.Length)
$ServiceDesc

- Part of the AI DevOps monorepo.
- Stored as a git subtree.
- Communicates with Orchestrator Service via async FastAPI APIs.
- Governance is tracked through the GitHub Governance Factory (submodule).
"""
"@
        $initContent | Out-File -FilePath "$ServiceName\src\__init__.py" -Encoding UTF8
        
        Write-Host "✓ Created basic structure for $ServiceName" -ForegroundColor Green
    }
}

# Process each service
foreach ($service in $services.Keys) {
    Setup-Subtree -ServiceName $service -ServiceDesc $services[$service]
}

Write-Host "`nMonorepo setup process initiated!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Verify all GitHub repositories were created" -ForegroundColor White
Write-Host "2. Check subtree configurations with: git log --oneline --graph" -ForegroundColor White
Write-Host "3. Test subtree operations:" -ForegroundColor White
Write-Host "   - Pull: git subtree pull --prefix=service-name repo-url master --squash" -ForegroundColor Gray
Write-Host "   - Push: git subtree push --prefix=service-name repo-url master" -ForegroundColor Gray
