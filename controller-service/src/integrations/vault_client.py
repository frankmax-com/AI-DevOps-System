"""
Azure Key Vault Client for Secure Secrets Management
Handles encryption keys, tokens, and sensitive configuration data
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from azure.keyvault.secrets import SecretClient
from azure.keyvault.keys import KeyClient, KeyType, KeyCurveName
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os
import base64

logger = logging.getLogger(__name__)

class VaultClient:
    """Azure Key Vault client for secrets and key management"""
    
    def __init__(self, vault_url: str, credential=None):
        """
        Initialize Azure Key Vault client
        
        Args:
            vault_url: Azure Key Vault URL (e.g., https://myvault.vault.azure.net/)
            credential: Azure credential (defaults to DefaultAzureCredential)
        """
        self.vault_url = vault_url
        
        # Initialize credentials
        if credential:
            self.credential = credential
        else:
            # Try to use service principal from environment variables
            client_id = os.getenv("AZURE_CLIENT_ID")
            client_secret = os.getenv("AZURE_CLIENT_SECRET")
            tenant_id = os.getenv("AZURE_TENANT_ID")
            
            if client_id and client_secret and tenant_id:
                self.credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=client_id,
                    client_secret=client_secret
                )
                logger.info("Using ClientSecretCredential from environment variables")
            else:
                self.credential = DefaultAzureCredential()
                logger.info("Using DefaultAzureCredential")
        
        # Initialize clients
        self.secret_client = SecretClient(vault_url=vault_url, credential=self.credential)
        self.key_client = KeyClient(vault_url=vault_url, credential=self.credential)
        
        # Cache for frequently accessed keys
        self._key_cache: Dict[str, Any] = {}
        self._cache_ttl = timedelta(minutes=30)
        self._cache_timestamps: Dict[str, datetime] = {}
    
    async def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from Key Vault
        
        Args:
            secret_name: Name of the secret
            
        Returns:
            Secret value or None if not found
        """
        try:
            secret = self.secret_client.get_secret(secret_name)
            logger.debug(f"Retrieved secret: {secret_name}")
            return secret.value
        except ResourceNotFoundError:
            logger.warning(f"Secret not found: {secret_name}")
            return None
        except HttpResponseError as e:
            logger.error(f"Error retrieving secret {secret_name}: {e}")
            raise
    
    async def set_secret(self, secret_name: str, secret_value: str, 
                        expires_on: Optional[datetime] = None,
                        tags: Optional[Dict[str, str]] = None) -> bool:
        """
        Store a secret in Key Vault
        
        Args:
            secret_name: Name of the secret
            secret_value: Secret value to store
            expires_on: Optional expiration datetime
            tags: Optional tags for the secret
            
        Returns:
            True if successful
        """
        try:
            self.secret_client.set_secret(
                name=secret_name,
                value=secret_value,
                expires_on=expires_on,
                tags=tags or {}
            )
            logger.info(f"Stored secret: {secret_name}")
            return True
        except HttpResponseError as e:
            logger.error(f"Error storing secret {secret_name}: {e}")
            raise
    
    async def delete_secret(self, secret_name: str) -> bool:
        """
        Delete a secret from Key Vault
        
        Args:
            secret_name: Name of the secret to delete
            
        Returns:
            True if successful
        """
        try:
            poller = self.secret_client.begin_delete_secret(secret_name)
            poller.wait()
            logger.info(f"Deleted secret: {secret_name}")
            return True
        except ResourceNotFoundError:
            logger.warning(f"Secret not found for deletion: {secret_name}")
            return False
        except HttpResponseError as e:
            logger.error(f"Error deleting secret {secret_name}: {e}")
            raise
    
    async def get_encryption_key(self, key_name: str) -> Optional[str]:
        """
        Retrieve an encryption key from Key Vault cache or vault
        
        Args:
            key_name: Name of the encryption key
            
        Returns:
            Base64-encoded public key or None if not found
        """
        # Check cache first
        if self._is_cached_and_valid(key_name):
            return self._key_cache[key_name]
        
        try:
            key = self.key_client.get_key(key_name)
            if key.key:
                # Convert to PEM format and base64 encode
                public_key_pem = key.key.to_dict()
                public_key_b64 = base64.b64encode(
                    json.dumps(public_key_pem).encode()
                ).decode()
                
                # Cache the key
                self._key_cache[key_name] = public_key_b64
                self._cache_timestamps[key_name] = datetime.utcnow()
                
                logger.debug(f"Retrieved encryption key: {key_name}")
                return public_key_b64
            
            return None
            
        except ResourceNotFoundError:
            logger.warning(f"Encryption key not found: {key_name}")
            return None
        except HttpResponseError as e:
            logger.error(f"Error retrieving key {key_name}: {e}")
            raise
    
    async def create_encryption_key(self, key_name: str, 
                                  key_type: str = "RSA",
                                  key_size: int = 2048,
                                  expires_on: Optional[datetime] = None,
                                  tags: Optional[Dict[str, str]] = None) -> str:
        """
        Create a new encryption key in Key Vault
        
        Args:
            key_name: Name for the new key
            key_type: Type of key (RSA, EC, etc.)
            key_size: Key size in bits
            expires_on: Optional expiration datetime
            tags: Optional tags for the key
            
        Returns:
            Base64-encoded public key
        """
        try:
            if key_type.upper() == "RSA":
                key = self.key_client.create_rsa_key(
                    name=key_name,
                    size=key_size,
                    expires_on=expires_on,
                    tags=tags or {}
                )
            elif key_type.upper() == "EC":
                key = self.key_client.create_ec_key(
                    name=key_name,
                    curve=KeyCurveName.p_256,
                    expires_on=expires_on,
                    tags=tags or {}
                )
            else:
                raise ValueError(f"Unsupported key type: {key_type}")
            
            # Convert to base64 for return
            public_key_pem = key.key.to_dict()
            public_key_b64 = base64.b64encode(
                json.dumps(public_key_pem).encode()
            ).decode()
            
            # Cache the new key
            self._key_cache[key_name] = public_key_b64
            self._cache_timestamps[key_name] = datetime.utcnow()
            
            logger.info(f"Created encryption key: {key_name}")
            return public_key_b64
            
        except HttpResponseError as e:
            logger.error(f"Error creating key {key_name}: {e}")
            raise
    
    async def encrypt_data(self, data: str, key_name: str) -> str:
        """
        Encrypt data using a Key Vault key
        
        Args:
            data: Data to encrypt
            key_name: Name of the encryption key
            
        Returns:
            Base64-encoded encrypted data
        """
        try:
            # For simplicity, we'll use local encryption with a derived key
            # In production, you might want to use Key Vault's encrypt operation
            
            # Get the key
            key_data = await self.get_encryption_key(key_name)
            if not key_data:
                raise ValueError(f"Encryption key not found: {key_name}")
            
            # Generate a symmetric key for actual encryption
            symmetric_key = os.urandom(32)  # 256-bit key
            iv = os.urandom(16)  # 128-bit IV
            
            # Encrypt data with symmetric key
            cipher = Cipher(
                algorithms.AES(symmetric_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Pad data to block size
            data_bytes = data.encode('utf-8')
            padding_length = 16 - (len(data_bytes) % 16)
            padded_data = data_bytes + bytes([padding_length]) * padding_length
            
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV and encrypted data
            result = iv + encrypted_data
            
            # Store the symmetric key in Key Vault for later decryption
            key_secret_name = f"{key_name}-symmetric-{datetime.utcnow().isoformat()}"
            await self.set_secret(
                key_secret_name,
                base64.b64encode(symmetric_key).decode(),
                expires_on=datetime.utcnow() + timedelta(days=1)
            )
            
            # Return encrypted data with key reference
            result_data = {
                "encrypted_data": base64.b64encode(result).decode(),
                "key_reference": key_secret_name
            }
            
            return base64.b64encode(json.dumps(result_data).encode()).decode()
            
        except Exception as e:
            logger.error(f"Error encrypting data with key {key_name}: {e}")
            raise
    
    async def decrypt_data(self, encrypted_data: str) -> str:
        """
        Decrypt data using a Key Vault key
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            
        Returns:
            Decrypted data
        """
        try:
            # Decode the encrypted data structure
            data_structure = json.loads(base64.b64decode(encrypted_data).decode())
            encrypted_bytes = base64.b64decode(data_structure["encrypted_data"])
            key_reference = data_structure["key_reference"]
            
            # Get the symmetric key
            symmetric_key_b64 = await self.get_secret(key_reference)
            if not symmetric_key_b64:
                raise ValueError(f"Symmetric key not found: {key_reference}")
            
            symmetric_key = base64.b64decode(symmetric_key_b64)
            
            # Extract IV and encrypted data
            iv = encrypted_bytes[:16]
            encrypted_content = encrypted_bytes[16:]
            
            # Decrypt
            cipher = Cipher(
                algorithms.AES(symmetric_key),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            decrypted_padded = decryptor.update(encrypted_content) + decryptor.finalize()
            
            # Remove padding
            padding_length = decrypted_padded[-1]
            decrypted_data = decrypted_padded[:-padding_length]
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error decrypting data: {e}")
            raise
    
    async def rotate_key(self, key_name: str) -> str:
        """
        Rotate an encryption key by creating a new version
        
        Args:
            key_name: Name of the key to rotate
            
        Returns:
            New key version identifier
        """
        try:
            # Create a new version of the existing key
            key = self.key_client.create_rsa_key(name=key_name, size=2048)
            
            # Clear cache for this key
            if key_name in self._key_cache:
                del self._key_cache[key_name]
                del self._cache_timestamps[key_name]
            
            logger.info(f"Rotated key: {key_name}, new version: {key.properties.version}")
            return key.properties.version
            
        except HttpResponseError as e:
            logger.error(f"Error rotating key {key_name}: {e}")
            raise
    
    async def list_secrets(self, max_page_size: int = 25) -> List[str]:
        """
        List all secret names in the vault
        
        Args:
            max_page_size: Maximum number of secrets per page
            
        Returns:
            List of secret names
        """
        try:
            secret_names = []
            for secret_properties in self.secret_client.list_properties_of_secrets(max_page_size=max_page_size):
                secret_names.append(secret_properties.name)
            
            logger.debug(f"Listed {len(secret_names)} secrets")
            return secret_names
            
        except HttpResponseError as e:
            logger.error(f"Error listing secrets: {e}")
            raise
    
    async def cleanup_expired_secrets(self) -> int:
        """
        Remove expired secrets from the vault
        
        Returns:
            Number of secrets cleaned up
        """
        try:
            cleaned_count = 0
            current_time = datetime.utcnow()
            
            for secret_properties in self.secret_client.list_properties_of_secrets():
                if (secret_properties.expires_on and 
                    secret_properties.expires_on < current_time):
                    
                    try:
                        self.secret_client.begin_delete_secret(secret_properties.name).wait()
                        cleaned_count += 1
                        logger.debug(f"Cleaned up expired secret: {secret_properties.name}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup secret {secret_properties.name}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} expired secrets")
            return cleaned_count
            
        except HttpResponseError as e:
            logger.error(f"Error during cleanup: {e}")
            raise
    
    async def get_tenant_encryption_key(self, tenant_id: str) -> str:
        """
        Get or create a tenant-specific encryption key
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Base64-encoded encryption key
        """
        key_name = f"tenant-{tenant_id}-encryption-key"
        
        # Try to get existing key
        key = await self.get_encryption_key(key_name)
        if key:
            return key
        
        # Create new key if not found
        logger.info(f"Creating new encryption key for tenant: {tenant_id}")
        return await self.create_encryption_key(
            key_name=key_name,
            tags={
                "tenant_id": tenant_id,
                "purpose": "tenant_encryption",
                "created_at": datetime.utcnow().isoformat()
            }
        )
    
    def _is_cached_and_valid(self, key_name: str) -> bool:
        """Check if a key is cached and still valid"""
        if key_name not in self._key_cache:
            return False
        
        cache_time = self._cache_timestamps.get(key_name)
        if not cache_time:
            return False
        
        return datetime.utcnow() - cache_time < self._cache_ttl
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the Key Vault connection
        
        Returns:
            Health status information
        """
        try:
            # Test secret operations
            test_secret_name = f"health-check-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            test_value = "health-check-value"
            
            # Set and get a test secret
            await self.set_secret(test_secret_name, test_value)
            retrieved_value = await self.get_secret(test_secret_name)
            
            # Clean up test secret
            await self.delete_secret(test_secret_name)
            
            # Verify operation
            secrets_healthy = retrieved_value == test_value
            
            # Test key operations
            try:
                keys_list = list(self.key_client.list_properties_of_keys(max_page_size=1))
                keys_healthy = True
            except Exception:
                keys_healthy = False
            
            return {
                "vault_url": self.vault_url,
                "secrets_healthy": secrets_healthy,
                "keys_healthy": keys_healthy,
                "overall_healthy": secrets_healthy and keys_healthy,
                "checked_at": datetime.utcnow().isoformat(),
                "cache_size": len(self._key_cache)
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "vault_url": self.vault_url,
                "secrets_healthy": False,
                "keys_healthy": False,
                "overall_healthy": False,
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }
