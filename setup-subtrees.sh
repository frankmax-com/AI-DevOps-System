#!/bin/bash

# AI DevOps Monorepo Setup Script
# This script sets up the proper git subtree structure for agent services

echo "Setting up AI DevOps monorepo with git subtrees..."

# Create repositories for each agent service
services=(
    "orchestrator-service:AI coordination layer"
    "dev-agent-service:Code generation and scaffolding"
    "qa-agent-service:Testing automation"
    "security-agent-service:Vulnerability scanning"
    "release-agent-service:Deployment automation"
    "pm-agent-service:Requirements and planning"
    "audit-service:Audit trails and compliance"
    "ai-provider-agent-service:AI routing and provider integration"
)

# Function to setup subtree for a service
setup_subtree() {
    local service_name=$1
    local service_desc=$2
    local repo_url="https://github.com/frankmax-com/${service_name}.git"
    
    echo "Setting up subtree for $service_name..."
    
    # Create temporary directory for the service
    temp_dir="../temp-${service_name}"
    mkdir -p "$temp_dir"
    
    # Initialize git repo and copy existing files
    cd "$temp_dir"
    git init
    
    # Copy existing service files if they exist
    if [ -d "../AI DevOps/${service_name}" ]; then
        cp -r "../AI DevOps/${service_name}/"* .
    else
        # Create basic structure
        mkdir -p src tests specs/{business,functional,implementation}
        
        # Create basic files
        cat > README.md << EOF
# ${service_name}

${service_desc}

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
EOF

        cat > requirements.txt << EOF
fastapi==0.104.1
uvicorn==0.24.0
pydantic==2.5.0
httpx==0.25.2
python-dotenv==1.0.0
structlog==23.2.0
EOF

        cat > src/__init__.py << EOF
"""
${service_name}
$(echo "$service_desc" | sed 's/./=/g')
${service_desc}

- Part of the AI DevOps monorepo.
- Stored as a git subtree.
- Communicates with Orchestrator Service via async FastAPI APIs.
- Governance is tracked through the GitHub Governance Factory (submodule).
"""
EOF
    fi
    
    git add .
    git commit -m "feat: initial ${service_name} setup

- Basic service structure
- FastAPI foundation
- Ready for subtree integration"
    
    git remote add origin "$repo_url"
    
    # Push to remote (this will fail if repo doesn't exist, which is expected)
    git push -u origin master 2>/dev/null || echo "Repository not yet created for $service_name"
    
    cd "../AI DevOps"
    
    # Remove existing directory if it exists
    if [ -d "$service_name" ]; then
        git rm -r "$service_name"
    fi
    
    # Add as subtree
    git subtree add --prefix="$service_name" "$repo_url" master --squash 2>/dev/null || echo "Will set up subtree for $service_name once repository is populated"
    
    # Clean up temp directory
    rm -rf "$temp_dir"
    
    echo "Completed setup for $service_name"
}

# Process each service
for service in "${services[@]}"; do
    IFS=':' read -r name desc <<< "$service"
    setup_subtree "$name" "$desc"
done

echo "Monorepo setup complete!"
echo ""
echo "Next steps:"
echo "1. Create individual repositories on GitHub for each service"
echo "2. Push the subtree content to each repository"
echo "3. Verify subtree links are working"
