# AI Provider Agent Service

A centralized AI provider routing service that intelligently distributes AI tasks across multiple providers while managing costs, quotas, and failover strategies.

## Features

- **Multi-Provider Support**: OpenAI, Anthropic, Google, HuggingFace, GitHub Copilot
- **Intelligent Routing**: Task-based model selection with automatic failover
- **Cost Optimization**: Free tier prioritization with quota management
- **Enterprise Ready**: Authentication, monitoring, and rate limiting
- **Containerized**: Docker and Docker Compose support
- **Scalable**: Async processing with Redis caching

## Quick Start

### 1. Clone and Setup

```bash
git clone <repository-url>
cd ai-provider-agent-service
```

### 2. Environment Configuration

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Run with Docker Compose

```bash
docker-compose up -d
```

### 4. Verify Installation

```bash
curl http://localhost:8080/health
```

## API Endpoints

### Health Check
```
GET /health
```

### AI Processing
```
POST /ai/process
Content-Type: application/json

{
  "task_type": "coding",
  "prompt": "Write a Python function to sort a list",
  "model": "auto",
  "max_tokens": 1000
}
```

### Provider Status
```
GET /providers/status
```

### Metrics
```
GET /metrics
```

## Configuration

### AI Providers

Edit `config/ai_providers_config.json` to configure providers:

```json
{
  "providers": [
    {
      "type": "openai_free",
      "api_key": null,
      "models": ["gpt-3.5-turbo", "gpt-4o-mini"],
      "daily_limit": 200,
      "rate_limit": 3,
      "priority": 2,
      "enabled": false
    }
  ]
}
```

### Environment Variables

Key environment variables:

- `AI_PROVIDER_CONFIG_PATH`: Path to provider configuration
- `REDIS_URL`: Redis connection string
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `ANTHROPIC_API_KEY`: Anthropic API key (optional)

## Task Types

The service supports various task types for intelligent routing:

- `THINKING`: General reasoning and problem-solving
- `CODING`: Code generation and debugging
- `WRITING`: Content creation and editing
- `ANALYSIS`: Data analysis and insights
- `VISION`: Image processing and analysis
- `SPEECH`: Audio processing and transcription
- `EMBEDDINGS`: Vector embeddings generation
- `CONVERSATION`: Chat and dialogue
- `REVIEW`: Code and content review
- `PLANNING`: Project and task planning

## Monitoring

### Prometheus Metrics

Access metrics at `http://localhost:9090`

Available metrics:
- Request counts and latencies
- Provider usage statistics
- Cost tracking
- Error rates

### Grafana Dashboards

Access dashboards at `http://localhost:3000`
- Username: admin
- Password: admin

## Integration Examples

### Python SDK

```python
import httpx

class AIProviderClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def process(self, task_type: str, prompt: str, **kwargs):
        response = await self.client.post(
            f"{self.base_url}/ai/process",
            json={
                "task_type": task_type,
                "prompt": prompt,
                **kwargs
            }
        )
        return response.json()

# Usage
client = AIProviderClient()
result = await client.process("coding", "Write a hello world function")
```

### Agent Service Integration

For other agent services (Dev Agent, QA Agent, etc.):

```python
from ai_provider_client import AIProviderClient

class DevAgent:
    def __init__(self):
        self.ai = AIProviderClient()
    
    async def generate_code(self, requirements: str):
        return await self.ai.process(
            task_type="coding",
            prompt=f"Generate code for: {requirements}",
            max_tokens=2000
        )
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis
docker run -d -p 6379:6379 redis:alpine

# Run the service
python -m uvicorn src.ai_provider_agent:app --reload --port 8080
```

### Testing

```bash
# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint
flake8 src/ tests/
mypy src/
```

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Dev Agent     │    │   QA Agent      │    │ Security Agent  │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │  AI Provider Agent Service  │
                    │                             │
                    │  ┌─────────────────────────┐│
                    │  │    Router Engine        ││
                    │  │  - Task-based routing   ││
                    │  │  - Intelligent failover ││
                    │  │  - Cost optimization    ││
                    │  └─────────────────────────┘│
                    └─────────────┬───────────────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
  ┌─────▼─────┐            ┌─────▼─────┐            ┌─────▼─────┐
  │  OpenAI   │            │ Anthropic │            │  Google   │
  │   Free    │            │   Free    │            │   Free    │
  └───────────┘            └───────────┘            └───────────┘
```

## Cost Management

The service prioritizes free tiers and includes cost tracking:

1. **Free Tier Priority**: Uses free providers first
2. **Quota Management**: Tracks daily limits per provider
3. **Cost Tracking**: Monitors token usage and costs
4. **Alerts**: Configurable cost and quota alerts

## Security

- JWT-based authentication
- Rate limiting per client
- API key secure storage
- Request/response logging
- Provider credential isolation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run quality checks
6. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create a GitHub issue
- Check the documentation
- Review the logs at `/app/logs/`
