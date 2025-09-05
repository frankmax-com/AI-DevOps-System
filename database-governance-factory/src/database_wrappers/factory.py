"""
Database Wrapper Factory
Central factory for creating database wrapper instances
"""

import logging
from typing import Dict, Any, Optional, Type, List
from enum import Enum

from .base_wrapper import BaseDatabaseWrapper, DatabaseConfig
from .mongodb_wrapper import MongoDBWrapper
from .postgresql_wrapper import PostgreSQLWrapper
from .redis_wrapper import RedisWrapper
from .cosmosdb_wrapper import CosmosDBWrapper
from .blobstorage_wrapper import BlobStorageWrapper

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """Supported database types"""
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    COSMOSDB = "cosmosdb"
    BLOBSTORAGE = "blobstorage"

class DatabaseWrapperFactory:
    """
    Factory class for creating database wrapper instances
    
    Provides a unified interface to create and manage database wrappers
    for all supported database types.
    """
    
    # Mapping of database types to wrapper classes
    WRAPPER_CLASSES: Dict[DatabaseType, Type[BaseDatabaseWrapper]] = {
        DatabaseType.MONGODB: MongoDBWrapper,
        DatabaseType.POSTGRESQL: PostgreSQLWrapper,
        DatabaseType.REDIS: RedisWrapper,
        DatabaseType.COSMOSDB: CosmosDBWrapper,
        DatabaseType.BLOBSTORAGE: BlobStorageWrapper,
    }
    
    # Registry of created wrapper instances
    _instances: Dict[str, BaseDatabaseWrapper] = {}
    
    @classmethod
    def create_wrapper(cls, config: DatabaseConfig) -> BaseDatabaseWrapper:
        """
        Create a database wrapper instance based on configuration
        
        Args:
            config: Database configuration containing type and connection info
            
        Returns:
            Database wrapper instance
            
        Raises:
            ValueError: If database type is not supported
            ImportError: If required database library is not installed
        """
        try:
            # Parse database type from config
            db_type = cls._parse_database_type(config)
            
            # Get wrapper class
            wrapper_class = cls.WRAPPER_CLASSES.get(db_type)
            if not wrapper_class:
                raise ValueError(f"Unsupported database type: {db_type}")
            
            # Create instance
            wrapper = wrapper_class(config)
            
            # Store in registry if instance_id is provided
            if config.instance_id:
                cls._instances[config.instance_id] = wrapper
            
            logger.info(f"Created {db_type.value} wrapper for {config.host}:{config.port}")
            return wrapper
            
        except Exception as e:
            logger.error(f"Failed to create database wrapper: {e}")
            raise
    
    @classmethod
    def get_wrapper(cls, instance_id: str) -> Optional[BaseDatabaseWrapper]:
        """
        Get existing wrapper instance by ID
        
        Args:
            instance_id: Unique identifier for the wrapper instance
            
        Returns:
            Database wrapper instance or None if not found
        """
        return cls._instances.get(instance_id)
    
    @classmethod
    def remove_wrapper(cls, instance_id: str) -> bool:
        """
        Remove wrapper instance from registry
        
        Args:
            instance_id: Unique identifier for the wrapper instance
            
        Returns:
            True if removed, False if not found
        """
        if instance_id in cls._instances:
            wrapper = cls._instances.pop(instance_id)
            # Attempt to disconnect
            try:
                if hasattr(wrapper, 'disconnect') and wrapper.is_connected:
                    import asyncio
                    if asyncio.get_event_loop().is_running():
                        asyncio.create_task(wrapper.disconnect())
                    else:
                        asyncio.run(wrapper.disconnect())
            except Exception as e:
                logger.warning(f"Error disconnecting wrapper {instance_id}: {e}")
            
            logger.info(f"Removed wrapper instance: {instance_id}")
            return True
        return False
    
    @classmethod
    def list_wrappers(cls) -> Dict[str, Dict[str, Any]]:
        """
        List all registered wrapper instances
        
        Returns:
            Dictionary mapping instance IDs to wrapper information
        """
        result = {}
        for instance_id, wrapper in cls._instances.items():
            result[instance_id] = {
                'type': wrapper.__class__.__name__,
                'host': wrapper.config.host,
                'port': wrapper.config.port,
                'database': wrapper.config.database_name,
                'is_connected': wrapper.is_connected,
                'created_at': wrapper.config.additional_config.get('created_at')
            }
        return result
    
    @classmethod
    def create_from_url(cls, database_url: str, **kwargs) -> BaseDatabaseWrapper:
        """
        Create wrapper from database URL
        
        Args:
            database_url: Database connection URL
            **kwargs: Additional configuration options
            
        Returns:
            Database wrapper instance
        """
        config = cls._parse_database_url(database_url, **kwargs)
        return cls.create_wrapper(config)
    
    @classmethod
    def create_mongodb_wrapper(cls, connection_string: str, database_name: str,
                             **kwargs) -> MongoDBWrapper:
        """
        Create MongoDB wrapper with connection string
        
        Args:
            connection_string: MongoDB connection string
            database_name: Database name
            **kwargs: Additional configuration
            
        Returns:
            MongoDB wrapper instance
        """
        config = DatabaseConfig(
            host="mongodb",
            port=27017,
            database_name=database_name,
            connection_string=connection_string,
            additional_config=kwargs
        )
        return cls.create_wrapper(config)
    
    @classmethod
    def create_postgresql_wrapper(cls, host: str, port: int, database: str,
                                username: str, password: str, **kwargs) -> PostgreSQLWrapper:
        """
        Create PostgreSQL wrapper with connection parameters
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            username: Username
            password: Password
            **kwargs: Additional configuration
            
        Returns:
            PostgreSQL wrapper instance
        """
        config = DatabaseConfig(
            host=host,
            port=port,
            database_name=database,
            username=username,
            password=password,
            additional_config=kwargs
        )
        return cls.create_wrapper(config)
    
    @classmethod
    def create_redis_wrapper(cls, host: str, port: int = 6379, database: int = 0,
                           password: str = None, **kwargs) -> RedisWrapper:
        """
        Create Redis wrapper with connection parameters
        
        Args:
            host: Redis host
            port: Redis port (default: 6379)
            database: Redis database number (default: 0)
            password: Redis password
            **kwargs: Additional configuration
            
        Returns:
            Redis wrapper instance
        """
        config = DatabaseConfig(
            host=host,
            port=port,
            database_name=str(database),
            password=password,
            additional_config=kwargs
        )
        return cls.create_wrapper(config)
    
    @classmethod
    def create_cosmosdb_wrapper(cls, endpoint: str, key: str, database_name: str,
                              **kwargs) -> CosmosDBWrapper:
        """
        Create Cosmos DB wrapper with connection parameters
        
        Args:
            endpoint: Cosmos DB endpoint URL
            key: Access key
            database_name: Database name
            **kwargs: Additional configuration
            
        Returns:
            Cosmos DB wrapper instance
        """
        config = DatabaseConfig(
            host=endpoint,
            port=443,
            database_name=database_name,
            password=key,  # Store key as password
            additional_config=kwargs
        )
        return cls.create_wrapper(config)
    
    @classmethod
    def create_blobstorage_wrapper(cls, connection_string: str, container_name: str,
                                 **kwargs) -> BlobStorageWrapper:
        """
        Create Blob Storage wrapper with connection parameters
        
        Args:
            connection_string: Azure Storage connection string
            container_name: Default container name
            **kwargs: Additional configuration
            
        Returns:
            Blob Storage wrapper instance
        """
        config = DatabaseConfig(
            host="blobstorage",
            port=443,
            database_name=container_name,
            connection_string=connection_string,
            additional_config=kwargs
        )
        return cls.create_wrapper(config)
    
    @classmethod
    async def test_all_connections(cls) -> Dict[str, bool]:
        """
        Test connections for all registered wrappers
        
        Returns:
            Dictionary mapping instance IDs to connection status
        """
        results = {}
        for instance_id, wrapper in cls._instances.items():
            try:
                if not wrapper.is_connected:
                    success = await wrapper.connect()
                else:
                    health = await wrapper.health_check()
                    success = health.is_healthy
                results[instance_id] = success
            except Exception as e:
                logger.error(f"Connection test failed for {instance_id}: {e}")
                results[instance_id] = False
        
        return results
    
    @classmethod
    async def disconnect_all(cls) -> None:
        """Disconnect all registered wrappers"""
        for instance_id, wrapper in cls._instances.items():
            try:
                if wrapper.is_connected:
                    await wrapper.disconnect()
                    logger.info(f"Disconnected wrapper: {instance_id}")
            except Exception as e:
                logger.error(f"Error disconnecting {instance_id}: {e}")
    
    @classmethod
    def get_supported_types(cls) -> List[str]:
        """
        Get list of supported database types
        
        Returns:
            List of supported database type names
        """
        return [db_type.value for db_type in DatabaseType]
    
    @classmethod
    def _parse_database_type(cls, config: DatabaseConfig) -> DatabaseType:
        """
        Parse database type from configuration
        
        Args:
            config: Database configuration
            
        Returns:
            Database type enum
            
        Raises:
            ValueError: If database type cannot be determined
        """
        # Check explicit type in additional_config
        if 'type' in config.additional_config:
            type_str = config.additional_config['type'].lower()
            for db_type in DatabaseType:
                if db_type.value == type_str:
                    return db_type
        
        # Infer from connection string
        if config.connection_string:
            conn_str = config.connection_string.lower()
            if 'mongodb' in conn_str or conn_str.startswith('mongodb://'):
                return DatabaseType.MONGODB
            elif 'postgresql' in conn_str or conn_str.startswith('postgresql://'):
                return DatabaseType.POSTGRESQL
            elif 'redis' in conn_str or conn_str.startswith('redis://'):
                return DatabaseType.REDIS
            elif 'cosmos' in conn_str or 'documents.azure.com' in conn_str:
                return DatabaseType.COSMOSDB
            elif 'blob' in conn_str or 'core.windows.net' in conn_str:
                return DatabaseType.BLOBSTORAGE
        
        # Infer from host/port
        if config.host:
            host = config.host.lower()
            if 'mongo' in host:
                return DatabaseType.MONGODB
            elif 'postgres' in host or config.port == 5432:
                return DatabaseType.POSTGRESQL
            elif 'redis' in host or config.port == 6379:
                return DatabaseType.REDIS
            elif 'cosmos' in host or 'documents.azure.com' in host:
                return DatabaseType.COSMOSDB
            elif 'blob' in host or 'core.windows.net' in host:
                return DatabaseType.BLOBSTORAGE
        
        raise ValueError("Could not determine database type from configuration")
    
    @classmethod
    def _parse_database_url(cls, url: str, **kwargs) -> DatabaseConfig:
        """
        Parse database URL into configuration
        
        Args:
            url: Database connection URL
            **kwargs: Additional configuration options
            
        Returns:
            Database configuration
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(url)
        
        # Extract basic components
        host = parsed.hostname or 'localhost'
        port = parsed.port or 0
        database_name = parsed.path.lstrip('/') if parsed.path else ''
        username = parsed.username
        password = parsed.password
        
        # Set default ports based on scheme
        if port == 0:
            if parsed.scheme in ['mongodb', 'mongodb+srv']:
                port = 27017
            elif parsed.scheme in ['postgresql', 'postgres']:
                port = 5432
            elif parsed.scheme == 'redis':
                port = 6379
            elif parsed.scheme == 'https':
                port = 443
        
        # Parse query parameters
        query_params = parse_qs(parsed.query)
        additional_config = {k: v[0] if len(v) == 1 else v for k, v in query_params.items()}
        additional_config.update(kwargs)
        
        # Add type based on scheme
        if parsed.scheme in ['mongodb', 'mongodb+srv']:
            additional_config['type'] = 'mongodb'
        elif parsed.scheme in ['postgresql', 'postgres']:
            additional_config['type'] = 'postgresql'
        elif parsed.scheme == 'redis':
            additional_config['type'] = 'redis'
        
        return DatabaseConfig(
            host=host,
            port=port,
            database_name=database_name,
            username=username,
            password=password,
            connection_string=url,
            additional_config=additional_config
        )

# Convenience functions for direct wrapper creation

async def create_and_connect(config: DatabaseConfig) -> BaseDatabaseWrapper:
    """
    Create wrapper and establish connection
    
    Args:
        config: Database configuration
        
    Returns:
        Connected database wrapper
        
    Raises:
        ConnectionError: If connection fails
    """
    wrapper = DatabaseWrapperFactory.create_wrapper(config)
    
    if not await wrapper.connect():
        raise ConnectionError(f"Failed to connect to {config.host}:{config.port}")
    
    return wrapper

def get_wrapper_info(wrapper: BaseDatabaseWrapper) -> Dict[str, Any]:
    """
    Get information about a wrapper instance
    
    Args:
        wrapper: Database wrapper instance
        
    Returns:
        Dictionary with wrapper information
    """
    return {
        'type': wrapper.__class__.__name__,
        'host': wrapper.config.host,
        'port': wrapper.config.port,
        'database': wrapper.config.database_name,
        'is_connected': wrapper.is_connected,
        'supported_operations': wrapper.get_supported_operations(),
        'created_at': wrapper.config.additional_config.get('created_at')
    }

# Default factory instance
default_factory = DatabaseWrapperFactory()
