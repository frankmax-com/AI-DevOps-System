"""
Mock Azure DevOps Governance Factory - POC Implementation  
Secure, auditable wrapper for Azure DevOps operations using ephemeral tokens
"""

import asyncio
import uuid
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json

# Use basic logging for POC
import logging
logger = logging.getLogger(__name__)

class AzureDevOpsGovernanceFactory:
    """
    Mock Azure DevOps operations with governance controls and audit trails
    """
    
    def __init__(self):
        self.mock_tokens = {}
        self.mock_resources = {}
        self.audit_entries = []
        
    async def mint_token(self, role_template: str, organization: str, ttl_minutes: int, 
                        reason: str, request_id: str) -> Dict[str, Any]:
        """
        Mint ephemeral token for Azure DevOps operations
        """
        try:
            token_id = str(uuid.uuid4())
            expires_at = datetime.utcnow() + timedelta(minutes=ttl_minutes)
            
            # Role-based scope mapping
            role_scopes = {
                "project_owner": ["vso.project_manage", "vso.work_write", "vso.code_write"],
                "repo_admin": ["vso.code_manage", "vso.build_execute"],
                "pipeline_admin": ["vso.build_write", "vso.release_write"],
                "dev": ["vso.code_write", "vso.work_write"],
                "ops": ["vso.build_execute", "vso.release_execute"]
            }
            
            scopes = role_scopes.get(role_template, ["vso.code_read"])
            
            # Generate mock token
            token_data = {
                "id": token_id,
                "token": f"azdo_mock_{token_id[:8]}***",
                "expires_at": expires_at.isoformat(),
                "scopes": scopes,
                "organization": organization,
                "role_template": role_template
            }
            
            self.mock_tokens[token_id] = token_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id,
                "timestamp": datetime.utcnow().isoformat(),
                "action": "mint_token",
                "resource_type": "azdo_token",
                "resource_id": token_id,
                "actor": "azure_governance_factory",
                "details": {
                    "role_template": role_template,
                    "organization": organization,
                    "ttl_minutes": ttl_minutes,
                    "reason": reason,
                    "scopes": scopes
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps token minted: {token_id}")
            
            return token_data
            
        except Exception as e:
            logger.error(f"Failed to mint Azure DevOps token: {e}")
            raise e
    
    async def create_project(self, token_id: str, organization: str, project_name: str, 
                            description: str = "", request_id: str = None) -> Dict[str, Any]:
        """
        Create Azure DevOps project with governance controls
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Invalid token")
                
            project_id = str(uuid.uuid4())
            
            project_data = {
                "id": project_id,
                "name": project_name,
                "description": description,
                "url": f"https://dev.azure.com/{organization}/{project_name}",
                "state": "wellFormed",
                "visibility": "private",
                "created_at": datetime.utcnow().isoformat(),
                "organization": organization
            }
            
            self.mock_resources[f"project_{project_id}"] = project_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "create_project",
                "resource_type": "azdo_project",
                "resource_id": project_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": organization,
                    "project_name": project_name,
                    "description": description
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps project created: {project_id}")
            
            return project_data
            
        except Exception as e:
            logger.error(f"Failed to create Azure DevOps project: {e}")
            raise e
    
    async def create_repository(self, token_id: str, organization: str, project_id: str, 
                               repo_name: str, request_id: str = None) -> Dict[str, Any]:
        """
        Create Azure DevOps repository with audit trail
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Invalid token")
                
            repo_id = str(uuid.uuid4())
            
            repo_data = {
                "id": repo_id,
                "name": repo_name,
                "url": f"https://dev.azure.com/{organization}/{project_id}/_git/{repo_name}",
                "project": {"id": project_id},
                "defaultBranch": "refs/heads/main",
                "created_at": datetime.utcnow().isoformat(),
                "organization": organization
            }
            
            self.mock_resources[f"repo_{repo_id}"] = repo_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "create_repository",
                "resource_type": "azdo_repository",
                "resource_id": repo_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": organization,
                    "project_id": project_id,
                    "repo_name": repo_name
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps repository created: {repo_id}")
            
            return repo_data
            
        except Exception as e:
            logger.error(f"Failed to create Azure DevOps repository: {e}")
            raise e
    
    async def create_pipeline_from_template(self, token_id: str, organization: str, 
                                           project_id: str, pipeline_name: str, 
                                           template_path: str, request_id: str = None) -> Dict[str, Any]:
        """
        Create Azure DevOps pipeline from template
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Invalid token")
                
            pipeline_id = str(uuid.uuid4())
            
            # Check if this requires approval
            requires_approval = "production" in pipeline_name.lower() or "deploy" in pipeline_name.lower()
            
            pipeline_data = {
                "id": pipeline_id,
                "name": pipeline_name,
                "project": {"id": project_id},
                "template_path": template_path,
                "created_at": datetime.utcnow().isoformat(),
                "organization": organization,
                "status": "pending_approval" if requires_approval else "active"
            }
            
            self.mock_resources[f"pipeline_{pipeline_id}"] = pipeline_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "create_pipeline_from_template",
                "resource_type": "azdo_pipeline",
                "resource_id": pipeline_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": organization,
                    "project_id": project_id,
                    "pipeline_name": pipeline_name,
                    "template_path": template_path,
                    "requires_approval": requires_approval
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps pipeline created: {pipeline_id}")
            
            return pipeline_data
            
        except Exception as e:
            logger.error(f"Failed to create Azure DevOps pipeline: {e}")
            raise e
    
    async def create_agent_pool(self, token_id: str, organization: str, pool_name: str, 
                               request_id: str = None) -> Dict[str, Any]:
        """
        Create Azure DevOps agent pool (mock - requires approval in production)
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Invalid token")
                
            pool_id = str(uuid.uuid4())
            
            # Agent pools always require approval for security
            pool_data = {
                "id": pool_id,
                "name": pool_name,
                "organization": organization,
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "approval_required": True
            }
            
            self.mock_resources[f"agentpool_{pool_id}"] = pool_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "create_agent_pool",
                "resource_type": "azdo_agent_pool",
                "resource_id": pool_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": organization,
                    "pool_name": pool_name,
                    "approval_required": True
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps agent pool creation requested: {pool_id} (pending approval)")
            
            return pool_data
            
        except Exception as e:
            logger.error(f"Failed to create Azure DevOps agent pool: {e}")
            raise e
    
    async def create_service_connection(self, token_id: str, organization: str, project_id: str, 
                                       connection_name: str, connection_type: str, 
                                       request_id: str = None) -> Dict[str, Any]:
        """
        Create service connection (always requires approval for security)
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Invalid token")
                
            connection_id = str(uuid.uuid4())
            
            # Service connections always require approval
            connection_data = {
                "id": connection_id,
                "name": connection_name,
                "type": connection_type,
                "project": {"id": project_id},
                "organization": organization,
                "status": "pending_approval",
                "created_at": datetime.utcnow().isoformat(),
                "approval_required": True
            }
            
            self.mock_resources[f"serviceconnection_{connection_id}"] = connection_data
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "create_service_connection",
                "resource_type": "azdo_service_connection",
                "resource_id": connection_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": organization,
                    "project_id": project_id,
                    "connection_name": connection_name,
                    "connection_type": connection_type,
                    "approval_required": True
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps service connection creation requested: {connection_id} (pending approval)")
            
            return connection_data
            
        except Exception as e:
            logger.error(f"Failed to create Azure DevOps service connection: {e}")
            raise e
    
    async def revoke_token(self, token_id: str, request_id: str = None) -> Dict[str, Any]:
        """
        Revoke ephemeral token
        """
        try:
            if token_id not in self.mock_tokens:
                raise ValueError("Token not found")
                
            token_data = self.mock_tokens[token_id]
            token_data["revoked"] = True
            token_data["revoked_at"] = datetime.utcnow().isoformat()
            
            # Audit entry
            audit_entry = {
                "request_id": request_id or str(uuid.uuid4()),
                "timestamp": datetime.utcnow().isoformat(),
                "action": "revoke_token",
                "resource_type": "azdo_token",
                "resource_id": token_id,
                "actor": "azure_governance_factory",
                "details": {
                    "organization": token_data.get("organization"),
                    "role_template": token_data.get("role_template")
                }
            }
            self.audit_entries.append(audit_entry)
            
            logger.info(f"Azure DevOps token revoked: {token_id}")
            
            return {"status": "revoked", "token_id": token_id}
            
        except Exception as e:
            logger.error(f"Failed to revoke Azure DevOps token: {e}")
            raise e
    
    def get_audit_entries(self) -> List[Dict[str, Any]]:
        """Get all audit entries"""
        return self.audit_entries.copy()
    
    def get_mock_resources(self) -> Dict[str, Any]:
        """Get all mock resources for testing"""
        return self.mock_resources.copy()
