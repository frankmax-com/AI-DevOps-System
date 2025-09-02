# AI DevOps System – Monorepo Structure

This repository is the **system of record** for the AI DevOps platform.

## Repo Architecture
- `orchestrator-service/` (subtree) → AI coordination layer
- `dev-agent-service/` (subtree) → Code generation + scaffolding
- `qa-agent-service/` (subtree) → Testing automation
- `security-agent-service/` (subtree) → Vulnerability scanning
- `release-agent-service/` (subtree) → Deployment automation
- `pm-agent-service/` (subtree) → Requirements & planning
- `audit-service/` (subtree) → Audit trails + compliance
- `ai-provider-agent-service/` (subtree) → AI routing & provider integration
- `github-governance-factory/` (submodule) → Governance factory (reusable across projects)

## Git Strategy
- **Subtrees** are used for agent services so code lives directly inside this repo.
- **Submodule** is used for `github-governance-factory` since it is reusable.

# Copilot Guidance: AI DevOps System

- Treat this repository as a **monorepo**.
- Agent services (orchestrator, dev-agent, qa-agent, etc.) are **subtrees**.
- The GitHub Governance Factory is a **submodule**.
- When generating code:
  - Place service-specific code in its respective folder.
  - Reuse common patterns from `orchestrator-service` for agent communication.
  - Assume inter-agent calls use HTTP (FastAPI) with async patterns.
- Always link issues, commits, and PRs back to GitHub Project items.

# Contributing Guidelines

## Subtrees (Agent Services)
To pull latest changes from an agent service upstream repo:
```bash
git subtree pull --prefix=dev-agent-service https://github.com/frankmax-com/dev-agent-service main --squash
```

To push changes back to the upstream repo:
```bash
git subtree push --prefix=dev-agent-service https://github.com/frankmax-com/dev-agent-service main
```

## Submodules (Governance Factory)
To update the governance factory:
```bash
git submodule update --remote github-governance-factory
git add github-governance-factory
git commit -m "Update governance factory to latest"
```

## Service Communication Patterns

### Standard Agent Service Structure
Each agent service should follow this pattern:

```
{service-name}/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── agent.py             # Core agent logic
│   ├── models.py            # Pydantic models
│   └── utils.py             # Helper functions
├── tests/
│   ├── test_agent.py
│   └── test_main.py
├── requirements.txt
├── Dockerfile
├── README.md
└── specs/                   # Business & technical specs
    ├── README.md
    ├── business/
    ├── functional/
    └── implementation/
```

### Agent Service Header Template
Every agent service should start with this docstring pattern:

```python
"""
{Service Name} Agent Service
============================
{Brief description of what this service does}

- Part of the AI DevOps monorepo.
- Stored as a git subtree.
- Communicates with Orchestrator Service via async FastAPI APIs.
- Governance is tracked through the GitHub Governance Factory (submodule).

Architecture:
- FastAPI for HTTP endpoints
- Async/await for non-blocking operations
- Pydantic models for data validation
- Docker containerization
- Health checks and monitoring
"""
```

### Inter-Service Communication
All agent services communicate through the Orchestrator Service using standardized patterns:

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import asyncio

class TaskRequest(BaseModel):
    task_id: str
    payload: dict
    context: dict = {}

class TaskResponse(BaseModel):
    task_id: str
    status: str  # "completed", "failed", "in_progress"
    result: dict = {}
    error: str = None

@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest):
    """Standard endpoint for receiving tasks from orchestrator"""
    try:
        # Process the task
        result = await process_task(request)
        return TaskResponse(
            task_id=request.task_id,
            status="completed",
            result=result
        )
    except Exception as e:
        return TaskResponse(
            task_id=request.task_id,
            status="failed",
            error=str(e)
        )
```

## GitHub Integration Patterns

### Issue Linking
All commits should reference GitHub issues:
```bash
git commit -m "feat: implement code generation logic

Implements core scaffolding functionality for dev agent.

Closes #123
Related to Epic #1"
```

### Project Board Integration
- Epic issues should be linked to Project milestones
- Feature issues should have clear acceptance criteria
- Task issues should estimate effort in story points
- All issues should have appropriate labels (service, priority, type)

## Development Workflow

### 1. Start with Specs
Before implementing any feature:
1. Create business requirements in `specs/business/`
2. Define functional requirements in `specs/functional/`
3. Create implementation plan in `specs/implementation/`

### 2. Create GitHub Issues
1. Create Epic for major features
2. Break down into Feature issues
3. Create Task issues for implementation details
4. Link all issues to the Project board

### 3. Implement with Tests
1. Write tests first (TDD approach)
2. Implement feature following the service patterns
3. Ensure all tests pass
4. Add integration tests for service communication

### 4. Document and Deploy
1. Update README.md with new functionality
2. Update API documentation
3. Create/update Docker configuration
4. Ensure monitoring and health checks work

## Monitoring and Observability

### Health Checks
Every service should implement:
```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "dev-agent-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }
```

### Logging Standards
Use structured logging:
```python
import logging
import json

logger = logging.getLogger(__name__)

def log_task_completion(task_id: str, status: str, duration: float):
    logger.info(json.dumps({
        "event": "task_completed",
        "task_id": task_id,
        "status": status,
        "duration_ms": duration * 1000,
        "service": "dev-agent-service"
    }))
```

## Security Considerations

### API Security
- All inter-service communication should use API keys
- Implement rate limiting
- Validate all input data with Pydantic models
- Use HTTPS in production

### Secret Management
- Never commit secrets to the repository
- Use environment variables for configuration
- Implement secret rotation policies
- Audit access to sensitive operations

## Performance Guidelines

### Async Best Practices
- Use async/await for I/O operations
- Implement connection pooling for external services
- Use background tasks for long-running operations
- Implement proper timeout handling

### Resource Management
- Implement proper cleanup in finally blocks
- Use context managers for resource handling
- Monitor memory usage and implement limits
- Implement graceful shutdown procedures

---

## Quick Reference

### Common Commands
```bash
# Pull all subtree updates
make update-subtrees

# Run all tests
make test

# Build all Docker images
make build

# Start development environment
make dev-up

# Check service health
make health-check
```

### Service URLs (Development)
- Orchestrator: http://localhost:8000
- Dev Agent: http://localhost:8001
- QA Agent: http://localhost:8002
- Security Agent: http://localhost:8003
- Release Agent: http://localhost:8004
- PM Agent: http://localhost:8005
- Audit Service: http://localhost:8006
- AI Provider Agent: http://localhost:8007

### Project Links
- GitHub Repository: https://github.com/frankmax-com/AI-DevOps-System
- Project Board: https://github.com/orgs/frankmax-com/projects/6
- Documentation: https://github.com/frankmax-com/AI-DevOps-System/wiki

---

*This document is maintained by the GitHub Governance Factory and updated automatically as the system evolves.*
