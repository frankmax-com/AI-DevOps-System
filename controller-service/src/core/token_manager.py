"""
Token Manager - Ephemeral token lifecycle management
Handles minting, validation, and revocation of short-lived agent tokens
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import uuid
import jwt
import structlog
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from ..models.agent_models import EphemeralToken
from ..integrations.vault_client import VaultClient

logger = structlog.get_logger()

class TokenManager:
    """
    Manages ephemeral tokens for autonomous agents
    Integrates with Azure Key Vault for secure key storage
    """
    
    def __init__(self):
        self.vault_client = VaultClient()
        self.active_tokens: Dict[str, EphemeralToken] = {}
        self.token_lineage: Dict[str, List[str]] = {}  # parent_id -> [child_ids]
        self.signing_key = None
        self.public_key = None
        
    async def initialize(self):
        """Initialize token manager with signing keys"""
        logger.info("Initializing Token Manager")
        
        # Get or create signing keys from Azure Key Vault
        await self._initialize_signing_keys()
        
        logger.info("Token Manager initialized")
    
    async def _initialize_signing_keys(self):
        """Initialize JWT signing keys from Azure Key Vault"""
        try:
            # Try to get existing keys from vault
            private_key_pem = await self.vault_client.get_secret("jwt-signing-key")
            
            if private_key_pem:
                self.signing_key = serialization.load_pem_private_key(
                    private_key_pem.encode(),
                    password=None
                )
            else:
                # Generate new key pair
                self.signing_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                
                # Store in vault
                private_pem = self.signing_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                )
                
                await self.vault_client.set_secret("jwt-signing-key", private_pem.decode())
            
            # Extract public key
            self.public_key = self.signing_key.public_key()
            
            logger.info("JWT signing keys initialized")
            
        except Exception as e:
            logger.error("Failed to initialize signing keys", error=str(e))
            raise e
    
    async def mint_token(
        self,
        agent_role: str,
        tenant_id: str,
        ttl_minutes: int,
        scopes: List[str],
        reason: str,
        parent_token_id: Optional[str] = None
    ) -> EphemeralToken:
        """
        Mint ephemeral token for agent operations
        
        Args:
            agent_role: Role of the requesting agent (founder, dev, ops, sec, finance)
            tenant_id: Startup tenant identifier for isolation
            ttl_minutes: Token time-to-live in minutes (max 60)
            scopes: List of allowed API scopes
            reason: Business justification for token request
            parent_token_id: Parent token for lineage tracking
        
        Returns:
            EphemeralToken with JWT and metadata
        """
        try:
            # Validate TTL limits
            if ttl_minutes > 60:
                raise ValueError("Maximum TTL is 60 minutes for security")
            
            if ttl_minutes < 5:
                raise ValueError("Minimum TTL is 5 minutes")
            
            # Generate token ID and timestamps
            token_id = str(uuid.uuid4())
            issued_at = datetime.utcnow()
            expires_at = issued_at + timedelta(minutes=ttl_minutes)
            
            # Validate scopes against agent role
            validated_scopes = await self._validate_agent_scopes(agent_role, scopes)
            
            # Create JWT payload
            jwt_payload = {
                "jti": token_id,  # JWT ID
                "iss": "controller-service",  # Issuer
                "sub": f"agent:{agent_role}",  # Subject
                "aud": "governance-factories",  # Audience
                "iat": int(issued_at.timestamp()),  # Issued at
                "exp": int(expires_at.timestamp()),  # Expires at
                "tenant_id": tenant_id,
                "agent_role": agent_role,
                "scopes": validated_scopes,
                "reason": reason,
                "parent_token_id": parent_token_id
            }
            
            # Sign JWT
            jwt_token = jwt.encode(
                jwt_payload,
                self.signing_key,
                algorithm="RS256"
            )
            
            # Create ephemeral token object
            ephemeral_token = EphemeralToken(
                token_id=token_id,
                jwt_token=jwt_token,
                agent_role=agent_role,
                tenant_id=tenant_id,
                scopes=validated_scopes,
                issued_at=issued_at,
                expires_at=expires_at,
                parent_token_id=parent_token_id,
                revoked=False,
                reason=reason
            )
            
            # Store in active tokens
            self.active_tokens[token_id] = ephemeral_token
            
            # Track lineage
            if parent_token_id:
                if parent_token_id not in self.token_lineage:
                    self.token_lineage[parent_token_id] = []
                self.token_lineage[parent_token_id].append(token_id)
            
            logger.info("Ephemeral token minted",
                       token_id=token_id,
                       agent_role=agent_role,
                       tenant_id=tenant_id,
                       ttl_minutes=ttl_minutes,
                       scopes=validated_scopes)
            
            return ephemeral_token
            
        except Exception as e:
            logger.error("Failed to mint token", error=str(e))
            raise e
    
    async def _validate_agent_scopes(
        self, 
        agent_role: str, 
        requested_scopes: List[str]
    ) -> List[str]:
        """Validate and filter scopes based on agent role permissions"""
        
        # Define role-based scope mappings
        role_scope_mappings = {
            "github_bootstrap": [
                "github:org:create",
                "github:repo:create", 
                "github:team:create",
                "github:actions:write",
                "github:secrets:write"
            ],
            "founder": [
                "ai:reasoning",
                "ai:analysis", 
                "ai:writing",
                "db:tenant:config:write",
                "db:business:metrics:read"
            ],
            "dev": [
                "azure:project:create",
                "azure:repo:write",
                "azure:pipeline:write",
                "azure:workitem:write",
                "github:repo:write"
            ],
            "ops": [
                "azure:pipeline:manage",
                "azure:serviceconnection:create",
                "azure:agentpool:manage",
                "azure:monitoring:write"
            ],
            "security": [
                "azure:security:scan",
                "azure:compliance:validate",
                "azure:policy:enforce",
                "github:security:read"
            ],
            "finance": [
                "db:cost:tracking:write",
                "db:budget:read",
                "azure:usage:read",
                "ai:cost:optimization"
            ]
        }
        
        # Get allowed scopes for role
        allowed_scopes = role_scope_mappings.get(agent_role, [])
        
        # Filter requested scopes to only allowed ones
        validated_scopes = [
            scope for scope in requested_scopes
            if scope in allowed_scopes
        ]
        
        if not validated_scopes:
            raise ValueError(f"No valid scopes for agent role {agent_role}")
        
        logger.info("Scopes validated",
                   agent_role=agent_role,
                   requested=requested_scopes,
                   validated=validated_scopes)
        
        return validated_scopes
    
    async def validate_token(self, jwt_token: str) -> Optional[EphemeralToken]:
        """
        Validate JWT token and return token metadata
        
        Args:
            jwt_token: JWT token string to validate
            
        Returns:
            EphemeralToken if valid, None if invalid
        """
        try:
            # Decode and verify JWT
            payload = jwt.decode(
                jwt_token,
                self.public_key,
                algorithms=["RS256"],
                audience="governance-factories",
                issuer="controller-service"
            )
            
            token_id = payload["jti"]
            
            # Check if token exists and is not revoked
            if token_id not in self.active_tokens:
                logger.warning("Token not found in active tokens", token_id=token_id)
                return None
            
            token = self.active_tokens[token_id]
            
            if token.revoked:
                logger.warning("Token has been revoked", token_id=token_id)
                return None
            
            # Check expiration
            if datetime.utcnow() > token.expires_at:
                logger.warning("Token has expired", token_id=token_id)
                # Auto-revoke expired token
                await self.revoke_token(token_id)
                return None
            
            logger.info("Token validated successfully", token_id=token_id)
            return token
            
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning("Invalid JWT token", error=str(e))
            return None
        except Exception as e:
            logger.error("Token validation error", error=str(e))
            return None
    
    async def revoke_token(self, token_id: str) -> Dict[str, Any]:
        """
        Revoke token and all child tokens
        
        Args:
            token_id: Token to revoke
            
        Returns:
            Revocation result with affected tokens
        """
        try:
            if token_id not in self.active_tokens:
                raise ValueError(f"Token {token_id} not found")
            
            revoked_tokens = []
            
            # Revoke the target token
            token = self.active_tokens[token_id]
            token.revoked = True
            token.revoked_at = datetime.utcnow()
            revoked_tokens.append(token_id)
            
            # Recursively revoke child tokens
            child_tokens = await self._get_child_tokens(token_id)
            for child_token_id in child_tokens:
                if child_token_id in self.active_tokens:
                    child_token = self.active_tokens[child_token_id]
                    child_token.revoked = True
                    child_token.revoked_at = datetime.utcnow()
                    revoked_tokens.append(child_token_id)
            
            logger.info("Tokens revoked",
                       primary_token=token_id,
                       revoked_count=len(revoked_tokens),
                       revoked_tokens=revoked_tokens)
            
            return {
                "revoked_tokens": revoked_tokens,
                "revocation_timestamp": datetime.utcnow(),
                "status": "success"
            }
            
        except Exception as e:
            logger.error("Failed to revoke token", token_id=token_id, error=str(e))
            raise e
    
    async def _get_child_tokens(self, parent_token_id: str) -> List[str]:
        """Recursively get all child tokens"""
        child_tokens = []
        
        direct_children = self.token_lineage.get(parent_token_id, [])
        child_tokens.extend(direct_children)
        
        # Recursively get children of children
        for child_id in direct_children:
            grandchildren = await self._get_child_tokens(child_id)
            child_tokens.extend(grandchildren)
        
        return child_tokens
    
    async def get_token_status(self, token_id: str) -> Dict[str, Any]:
        """Get detailed token status and metadata"""
        
        if token_id not in self.active_tokens:
            return {"status": "not_found"}
        
        token = self.active_tokens[token_id]
        
        status = "active"
        if token.revoked:
            status = "revoked"
        elif datetime.utcnow() > token.expires_at:
            status = "expired"
        
        return {
            "token_id": token_id,
            "status": status,
            "agent_role": token.agent_role,
            "tenant_id": token.tenant_id,
            "scopes": token.scopes,
            "issued_at": token.issued_at,
            "expires_at": token.expires_at,
            "revoked_at": getattr(token, 'revoked_at', None),
            "parent_token_id": token.parent_token_id,
            "child_tokens": self.token_lineage.get(token_id, []),
            "reason": token.reason
        }
    
    async def cleanup_expired_tokens(self):
        """Background task to cleanup expired tokens"""
        try:
            current_time = datetime.utcnow()
            expired_tokens = []
            
            for token_id, token in self.active_tokens.items():
                if current_time > token.expires_at and not token.revoked:
                    token.revoked = True
                    token.revoked_at = current_time
                    expired_tokens.append(token_id)
            
            if expired_tokens:
                logger.info("Cleaned up expired tokens", 
                           count=len(expired_tokens),
                           tokens=expired_tokens)
            
        except Exception as e:
            logger.error("Failed to cleanup expired tokens", error=str(e))
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get token manager metrics"""
        current_time = datetime.utcnow()
        
        active_count = len([
            t for t in self.active_tokens.values()
            if not t.revoked and current_time <= t.expires_at
        ])
        
        expired_count = len([
            t for t in self.active_tokens.values()
            if current_time > t.expires_at
        ])
        
        revoked_count = len([
            t for t in self.active_tokens.values()
            if t.revoked
        ])
        
        return {
            "total_tokens": len(self.active_tokens),
            "active_tokens": active_count,
            "expired_tokens": expired_count,
            "revoked_tokens": revoked_count,
            "token_lineages": len(self.token_lineage),
            "last_updated": current_time
        }
    
    async def cleanup(self):
        """Cleanup on service shutdown"""
        logger.info("Cleaning up Token Manager")
        
        # Revoke all active tokens
        active_tokens = [
            token_id for token_id, token in self.active_tokens.items()
            if not token.revoked and datetime.utcnow() <= token.expires_at
        ]
        
        for token_id in active_tokens:
            await self.revoke_token(token_id)
        
        logger.info("Token Manager cleanup completed",
                   revoked_count=len(active_tokens))
