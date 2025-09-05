"""
Database Wrappers Package
Comprehensive database wrapper system for multiple database types

Provides unified interfaces for:
- MongoDB
- PostgreSQL 
- Redis
- Azure Cosmos DB
- Azure Blob Storage

Complete functionality includes:
- CRUD operations
- Schema management
- Indexing
- Transactions
- Backup/Recovery
- Performance monitoring
- Streaming support
"""

# Import base classes
from .base_wrapper import (
    BaseDatabaseWrapper,
    DatabaseConfig,
    DatabaseOperation,
    QueryResult,
    HealthStatus,
    BackupInfo,
    OperationType,
    DatabaseWrapperMixin
)

# Import specific wrappers
from .mongodb_wrapper import MongoDBWrapper
from .postgresql_wrapper import PostgreSQLWrapper
from .redis_wrapper import RedisWrapper
from .cosmosdb_wrapper import CosmosDBWrapper
from .blobstorage_wrapper import BlobStorageWrapper

# Import factory
from .factory import (
    DatabaseWrapperFactory,
    DatabaseType,
    create_and_connect,
    get_wrapper_info,
    default_factory
)

# Public API
__all__ = [
    # Base classes
    'BaseDatabaseWrapper',
    'DatabaseConfig',
    'DatabaseOperation',
    'QueryResult',
    'HealthStatus',
    'BackupInfo',
    'OperationType',
    'DatabaseWrapperMixin',
    
    # Wrapper implementations
    'MongoDBWrapper',
    'PostgreSQLWrapper',
    'RedisWrapper',
    'CosmosDBWrapper',
    'BlobStorageWrapper',
    
    # Factory and utilities
    'DatabaseWrapperFactory',
    'DatabaseType',
    'create_and_connect',
    'get_wrapper_info',
    'default_factory',
]

__version__ = "1.0.0"
