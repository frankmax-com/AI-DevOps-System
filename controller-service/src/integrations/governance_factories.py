"""
Governance Factories Integration Layer
Provides unified interface to all governance factory services
"""

import asyncio
import aiohttp
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import os

logger = logging.getLogger(__name__)

@dataclass
class GovernanceFactoryConfig:
    """Configuration for a governance factory"""
    name: str
    base_url: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    health_endpoint: str = "/health"
    version: str = "v1"

class GovernanceFactoryClient:
    """Base client for governance factory services"""
    
    def __init__(self, config: GovernanceFactoryConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None
        self._last_health_check: Optional[datetime] = None
        self._health_status: bool = False
        
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
    
    async def connect(self):
        """Initialize HTTP session"""
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout)
        self.session = aiohttp.ClientSession(
            headers=headers,
            timeout=timeout,
            connector=aiohttp.TCPConnector(limit=10)
        )
        
        # Perform initial health check
        await self.health_check()
    
    async def disconnect(self):
        """Close HTTP session"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def _make_request(self, method: str, endpoint: str, 
                          data: Optional[Dict] = None,
                          params: Optional[Dict] = None,
                          retries: int = 0) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        if not self.session:
            raise RuntimeError("Client not connected")
        
        url = f"{self.config.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            kwargs = {"params": params} if params else {}
            if data:
                kwargs["json"] = data
            
            async with self.session.request(method, url, **kwargs) as response:
                response_data = await response.json()
                
                if response.status >= 400:
                    logger.error(f"Request failed: {method} {url}, Status: {response.status}, Data: {response_data}")
                    if retries < self.config.max_retries:
                        await asyncio.sleep(2 ** retries)  # Exponential backoff
                        return await self._make_request(method, endpoint, data, params, retries + 1)
                    
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=f"HTTP {response.status}: {response_data.get('detail', 'Unknown error')}"
                    )
                
                return response_data
                
        except aiohttp.ClientError as e:
            logger.error(f"Request error: {method} {url}, Error: {e}")
            if retries < self.config.max_retries:
                await asyncio.sleep(2 ** retries)
                return await self._make_request(method, endpoint, data, params, retries + 1)
            raise
    
    async def health_check(self) -> bool:
        """Check health of the governance factory"""
        try:
            response = await self._make_request("GET", self.config.health_endpoint)
            self._health_status = response.get("status") == "healthy"
            self._last_health_check = datetime.utcnow()
            
            logger.debug(f"Health check for {self.config.name}: {'✓' if self._health_status else '✗'}")
            return self._health_status
            
        except Exception as e:
            logger.warning(f"Health check failed for {self.config.name}: {e}")
            self._health_status = False
            self._last_health_check = datetime.utcnow()
            return False
    
    @property
    def is_healthy(self) -> bool:
        """Check if service is healthy (with cache)"""
        if not self._last_health_check:
            return False
        
        # Cache health status for 5 minutes
        cache_expiry = self._last_health_check + timedelta(minutes=5)
        if datetime.utcnow() > cache_expiry:
            return False
        
        return self._health_status

class GitHubGovernanceClient(GovernanceFactoryClient):
    """Client for GitHub Governance Factory"""
    
    async def create_organization(self, startup_id: str, org_name: str, 
                                admin_email: str) -> Dict[str, Any]:
        """Create a new GitHub organization"""
        data = {
            "startup_id": startup_id,
            "org_name": org_name,
            "admin_email": admin_email,
            "settings": {
                "private_repos_enabled": True,
                "two_factor_required": True,
                "default_permissions": "read"
            }
        }
        return await self._make_request("POST", "/api/v1/organizations", data)
    
    async def create_repository(self, startup_id: str, org_name: str, 
                              repo_name: str, template: Optional[str] = None) -> Dict[str, Any]:
        """Create a repository in the organization"""
        data = {
            "startup_id": startup_id,
            "org_name": org_name,
            "repo_name": repo_name,
            "template": template,
            "private": True,
            "settings": {
                "has_issues": True,
                "has_projects": True,
                "has_wiki": False,
                "allow_merge_commit": False,
                "allow_squash_merge": True,
                "allow_rebase_merge": False
            }
        }
        return await self._make_request("POST", "/api/v1/repositories", data)
    
    async def setup_branch_protection(self, startup_id: str, org_name: str,
                                     repo_name: str, branch: str = "main") -> Dict[str, Any]:
        """Setup branch protection rules"""
        data = {
            "startup_id": startup_id,
            "org_name": org_name,
            "repo_name": repo_name,
            "branch": branch,
            "protection": {
                "required_status_checks": {
                    "strict": True,
                    "contexts": ["continuous-integration"]
                },
                "enforce_admins": True,
                "required_pull_request_reviews": {
                    "required_approving_review_count": 2,
                    "dismiss_stale_reviews": True,
                    "require_code_owner_reviews": True
                },
                "restrictions": None
            }
        }
        return await self._make_request("POST", "/api/v1/branch-protection", data)

class AzureDevOpsGovernanceClient(GovernanceFactoryClient):
    """Client for Azure DevOps Governance Factory"""
    
    async def create_project(self, startup_id: str, project_name: str,
                           description: str) -> Dict[str, Any]:
        """Create a new Azure DevOps project"""
        data = {
            "startup_id": startup_id,
            "project_name": project_name,
            "description": description,
            "capabilities": {
                "versioncontrol": {"sourceControlType": "Git"},
                "processTemplate": {"templateTypeId": "adcc42ab-9882-485e-a3ed-7678f01f66bc"}  # Agile
            },
            "visibility": "private"
        }
        return await self._make_request("POST", "/api/v1/projects", data)
    
    async def setup_build_pipeline(self, startup_id: str, project_name: str,
                                  repo_url: str, pipeline_name: str) -> Dict[str, Any]:
        """Setup CI/CD build pipeline"""
        data = {
            "startup_id": startup_id,
            "project_name": project_name,
            "pipeline_name": pipeline_name,
            "repository": {
                "url": repo_url,
                "type": "GitHub"
            },
            "configuration": {
                "type": "yaml",
                "path": "/.azure-pipelines.yml"
            },
            "settings": {
                "enforce_variable_security": True,
                "status_badge_enabled": True,
                "auto_trigger_on_pr": True
            }
        }
        return await self._make_request("POST", "/api/v1/pipelines", data)
    
    async def create_service_connection(self, startup_id: str, project_name: str,
                                      connection_name: str, connection_type: str,
                                      config: Dict[str, Any]) -> Dict[str, Any]:
        """Create service connection for external integrations"""
        data = {
            "startup_id": startup_id,
            "project_name": project_name,
            "connection_name": connection_name,
            "connection_type": connection_type,
            "configuration": config,
            "is_shared": False,
            "is_ready": True
        }
        return await self._make_request("POST", "/api/v1/service-connections", data)

class AIProviderGovernanceClient(GovernanceFactoryClient):
    """Client for AI Provider Governance Factory"""
    
    async def configure_tenant(self, startup_id: str, tenant_config: Dict[str, Any]) -> Dict[str, Any]:
        """Configure AI provider access for tenant"""
        data = {
            "startup_id": startup_id,
            "tenant_config": tenant_config,
            "providers": {
                "openai": {"enabled": True, "tier": "pro"},
                "anthropic": {"enabled": True, "tier": "team"},
                "azure_openai": {"enabled": True, "tier": "standard"},
                "google": {"enabled": False},
                "aws_bedrock": {"enabled": False}
            },
            "quotas": {
                "requests_per_hour": 1000,
                "requests_per_day": 10000,
                "max_tokens_per_request": 8192
            }
        }
        return await self._make_request("POST", "/api/v1/tenant-config", data)
    
    async def get_usage_metrics(self, startup_id: str, 
                               start_date: datetime,
                               end_date: datetime) -> Dict[str, Any]:
        """Get AI usage metrics for tenant"""
        params = {
            "startup_id": startup_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
        return await self._make_request("GET", "/api/v1/usage-metrics", params=params)

class DatabaseGovernanceClient(GovernanceFactoryClient):
    """Client for Database Governance Factory"""
    
    async def create_tenant_database(self, startup_id: str, 
                                   database_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create tenant-specific database"""
        data = {
            "startup_id": startup_id,
            "database_config": database_config,
            "encryption": {
                "enabled": True,
                "key_rotation": True,
                "backup_encryption": True
            },
            "access_control": {
                "rbac_enabled": True,
                "audit_enabled": True,
                "connection_limits": 100
            }
        }
        return await self._make_request("POST", "/api/v1/tenant-database", data)
    
    async def execute_migration(self, startup_id: str, migration_id: str,
                               migration_sql: str) -> Dict[str, Any]:
        """Execute database migration"""
        data = {
            "startup_id": startup_id,
            "migration_id": migration_id,
            "migration_sql": migration_sql,
            "rollback_sql": "",
            "dry_run": False
        }
        return await self._make_request("POST", "/api/v1/migrations", data)

class GovernanceFactoryManager:
    """Manager for all governance factory clients"""
    
    def __init__(self):
        self.clients: Dict[str, GovernanceFactoryClient] = {}
        self._initialized = False
    
    async def initialize(self, configs: Dict[str, GovernanceFactoryConfig]):
        """Initialize all governance factory clients"""
        if self._initialized:
            return
        
        # Create clients
        self.clients["github"] = GitHubGovernanceClient(configs["github"])
        self.clients["azure"] = AzureDevOpsGovernanceClient(configs["azure"])
        self.clients["ai_provider"] = AIProviderGovernanceClient(configs["ai_provider"])
        self.clients["database"] = DatabaseGovernanceClient(configs["database"])
        
        # Connect all clients
        connection_tasks = [client.connect() for client in self.clients.values()]
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        self._initialized = True
        logger.info("Governance factory manager initialized")
    
    async def shutdown(self):
        """Shutdown all clients"""
        if not self._initialized:
            return
        
        disconnect_tasks = [client.disconnect() for client in self.clients.values()]
        await asyncio.gather(*disconnect_tasks, return_exceptions=True)
        
        self._initialized = False
        logger.info("Governance factory manager shutdown")
    
    def get_client(self, factory_name: str) -> GovernanceFactoryClient:
        """Get a governance factory client by name"""
        if not self._initialized:
            raise RuntimeError("Manager not initialized")
        
        if factory_name not in self.clients:
            raise ValueError(f"Unknown governance factory: {factory_name}")
        
        client = self.clients[factory_name]
        if not client.is_healthy:
            logger.warning(f"Governance factory {factory_name} is not healthy")
        
        return client
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Perform health check on all governance factories"""
        health_tasks = {
            name: client.health_check() 
            for name, client in self.clients.items()
        }
        
        results = await asyncio.gather(*health_tasks.values(), return_exceptions=True)
        
        health_status = {}
        for name, result in zip(health_tasks.keys(), results):
            if isinstance(result, Exception):
                health_status[name] = False
                logger.error(f"Health check failed for {name}: {result}")
            else:
                health_status[name] = result
        
        return health_status
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        health_status = await self.health_check_all()
        
        return {
            "governance_factories": {
                name: {
                    "healthy": status,
                    "url": client.config.base_url,
                    "last_check": client._last_health_check.isoformat() if client._last_health_check else None
                }
                for name, (status, client) in zip(health_status.keys(), 
                                                 zip(health_status.values(), self.clients.values()))
            },
            "overall_healthy": all(health_status.values()),
            "checked_at": datetime.utcnow().isoformat()
        }

# Global manager instance
governance_manager = GovernanceFactoryManager()

async def get_governance_manager() -> GovernanceFactoryManager:
    """Get the global governance manager instance"""
    if not governance_manager._initialized:
        # Load configuration from environment
        configs = {
            "github": GovernanceFactoryConfig(
                name="github",
                base_url=os.getenv("GITHUB_GOVERNANCE_URL", "http://localhost:8001"),
                api_key=os.getenv("GITHUB_GOVERNANCE_API_KEY")
            ),
            "azure": GovernanceFactoryConfig(
                name="azure",
                base_url=os.getenv("AZURE_GOVERNANCE_URL", "http://localhost:8002"),
                api_key=os.getenv("AZURE_GOVERNANCE_API_KEY")
            ),
            "ai_provider": GovernanceFactoryConfig(
                name="ai_provider",
                base_url=os.getenv("AI_PROVIDER_GOVERNANCE_URL", "http://localhost:8003"),
                api_key=os.getenv("AI_PROVIDER_GOVERNANCE_API_KEY")
            ),
            "database": GovernanceFactoryConfig(
                name="database",
                base_url=os.getenv("DATABASE_GOVERNANCE_URL", "http://localhost:8004"),
                api_key=os.getenv("DATABASE_GOVERNANCE_API_KEY")
            )
        }
        
        await governance_manager.initialize(configs)
    
    return governance_manager
