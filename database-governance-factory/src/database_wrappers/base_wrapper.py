"""
Base Database Wrapper
Abstract base class for all database wrappers providing unified interface
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """Supported database types"""
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    COSMOS_DB = "cosmos_db"
    BLOB_STORAGE = "blob_storage"

class OperationType(Enum):
    """Database operation types"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    AGGREGATE = "aggregate"
    INDEX = "index"
    BACKUP = "backup"
    RESTORE = "restore"
    HEALTH_CHECK = "health_check"

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    name: str
    db_type: DatabaseType
    connection_string: str
    database_name: str
    additional_config: Dict[str, Any] = None
    pool_size: int = 10
    timeout: int = 30
    ssl_enabled: bool = False
    
    def __post_init__(self):
        if self.additional_config is None:
            self.additional_config = {}

@dataclass
class DatabaseOperation:
    """Database operation metadata"""
    operation_id: str
    operation_type: OperationType
    table_or_collection: str
    timestamp: datetime
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    affected_records: int = 0
    query_details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.query_details is None:
            self.query_details = {}

@dataclass
class QueryResult:
    """Standardized query result"""
    success: bool
    data: Any
    count: int = 0
    error_message: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class HealthStatus:
    """Database health status"""
    is_healthy: bool
    response_time_ms: float
    version: str
    connection_count: int = 0
    memory_usage_mb: float = 0
    disk_usage_mb: float = 0
    error_message: Optional[str] = None
    last_check: datetime = None
    additional_metrics: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.additional_metrics is None:
            self.additional_metrics = {}
        if self.last_check is None:
            self.last_check = datetime.utcnow()

@dataclass
class BackupInfo:
    """Backup operation information"""
    backup_id: str
    backup_type: str  # full, incremental, differential
    size_mb: float
    location: str
    timestamp: datetime
    duration_ms: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseDatabaseWrapper(ABC):
    """
    Abstract base class for all database wrappers
    Provides unified interface for all database operations
    """
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.connection = None
        self.is_connected = False
        self.connection_pool = None
        self.operation_history: List[DatabaseOperation] = []
        
    @abstractmethod
    async def connect(self) -> bool:
        """Establish database connection"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """Close database connection"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Check database health and performance metrics"""
        pass
    
    # === CRUD Operations ===
    
    @abstractmethod
    async def create(self, table_or_collection: str, data: Union[Dict, List[Dict]], 
                    options: Dict[str, Any] = None) -> QueryResult:
        """Create/Insert new records"""
        pass
    
    @abstractmethod
    async def read(self, table_or_collection: str, query: Dict[str, Any] = None,
                  projection: Dict[str, Any] = None, limit: int = None, 
                  offset: int = None, sort: Dict[str, Any] = None) -> QueryResult:
        """Read/Select records with optional filtering, projection, and pagination"""
        pass
    
    @abstractmethod
    async def update(self, table_or_collection: str, query: Dict[str, Any],
                    update_data: Dict[str, Any], options: Dict[str, Any] = None) -> QueryResult:
        """Update existing records"""
        pass
    
    @abstractmethod
    async def delete(self, table_or_collection: str, query: Dict[str, Any],
                    options: Dict[str, Any] = None) -> QueryResult:
        """Delete records"""
        pass
    
    # === Advanced Query Operations ===
    
    @abstractmethod
    async def query(self, query: str, parameters: List[Any] = None) -> QueryResult:
        """Execute raw query (SQL, MongoDB query, etc.)"""
        pass
    
    @abstractmethod
    async def aggregate(self, table_or_collection: str, pipeline: List[Dict[str, Any]]) -> QueryResult:
        """Execute aggregation pipeline"""
        pass
    
    @abstractmethod
    async def batch_operation(self, operations: List[Dict[str, Any]]) -> List[QueryResult]:
        """Execute multiple operations in batch"""
        pass
    
    # === Schema Management ===
    
    @abstractmethod
    async def create_table_or_collection(self, name: str, schema: Dict[str, Any] = None) -> bool:
        """Create new table/collection with optional schema"""
        pass
    
    @abstractmethod
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop table/collection"""
        pass
    
    @abstractmethod
    async def list_tables_or_collections(self) -> List[str]:
        """List all tables/collections"""
        pass
    
    @abstractmethod
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get table/collection schema"""
        pass
    
    # === Index Management ===
    
    @abstractmethod
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Create index"""
        pass
    
    @abstractmethod
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Drop index"""
        pass
    
    @abstractmethod
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """List all indexes for table/collection"""
        pass
    
    # === Transaction Support ===
    
    @abstractmethod
    async def begin_transaction(self) -> Any:
        """Begin transaction (if supported)"""
        pass
    
    @abstractmethod
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit transaction"""
        pass
    
    @abstractmethod
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback transaction"""
        pass
    
    # === Backup and Recovery ===
    
    @abstractmethod
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Create database backup"""
        pass
    
    @abstractmethod
    async def restore_backup(self, backup_info: BackupInfo, 
                           restore_config: Dict[str, Any] = None) -> bool:
        """Restore from backup"""
        pass
    
    @abstractmethod
    async def list_backups(self) -> List[BackupInfo]:
        """List available backups"""
        pass
    
    # === Monitoring and Statistics ===
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics"""
        pass
    
    @abstractmethod
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        pass
    
    @abstractmethod
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries log"""
        pass
    
    # === Utility Methods ===
    
    async def execute_with_retry(self, operation_func, max_retries: int = 3, 
                                delay_seconds: float = 1.0) -> Any:
        """Execute operation with retry logic"""
        import asyncio
        
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return await operation_func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}")
                    await asyncio.sleep(delay_seconds * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Operation failed after {max_retries + 1} attempts: {e}")
                    
        raise last_exception
    
    def log_operation(self, operation: DatabaseOperation):
        """Log database operation for monitoring"""
        self.operation_history.append(operation)
        
        # Keep only last 1000 operations
        if len(self.operation_history) > 1000:
            self.operation_history = self.operation_history[-1000:]
    
    def get_operation_history(self, limit: int = 100) -> List[DatabaseOperation]:
        """Get recent operation history"""
        return self.operation_history[-limit:]
    
    async def validate_connection(self) -> bool:
        """Validate that connection is still active"""
        try:
            health = await self.health_check()
            return health.is_healthy
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information"""
        return {
            'database_name': self.config.database_name,
            'database_type': self.config.db_type.value,
            'is_connected': self.is_connected,
            'pool_size': self.config.pool_size,
            'timeout': self.config.timeout,
            'ssl_enabled': self.config.ssl_enabled
        }
    
    # === Context Manager Support ===
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.disconnect()
        return False
    
    # === Streaming Support ===
    
    @abstractmethod
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream large datasets in batches"""
        pass
    
    # === Data Validation ===
    
    def validate_data(self, data: Any, schema: Dict[str, Any] = None) -> bool:
        """Validate data against schema (basic implementation)"""
        if schema is None:
            return True
        
        # Basic validation - can be extended in specific implementations
        if isinstance(data, dict) and 'required_fields' in schema:
            required_fields = schema['required_fields']
            return all(field in data for field in required_fields)
        
        return True
    
    # === Connection Pool Management ===
    
    @abstractmethod
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pass
    
    @abstractmethod
    async def reset_pool(self) -> bool:
        """Reset connection pool"""
        pass
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get list of database-specific operations available"""
        # Each implementation can override this to provide specific operations
        return []
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute database-specific operation"""
        raise NotImplementedError(f"Database-specific operation '{operation_name}' not implemented")


class DatabaseWrapperMixin:
    """Mixin providing common functionality for database wrappers"""
    
    def format_error_message(self, operation: str, error: Exception) -> str:
        """Format error message for logging"""
        return f"Error in {operation}: {type(error).__name__}: {str(error)}"
    
    def create_operation_metadata(self, operation_type: OperationType, 
                                 table_or_collection: str, 
                                 start_time: datetime,
                                 success: bool, 
                                 error_message: str = None,
                                 affected_records: int = 0) -> DatabaseOperation:
        """Create operation metadata for logging"""
        import uuid
        end_time = datetime.utcnow()
        duration_ms = (end_time - start_time).total_seconds() * 1000
        
        return DatabaseOperation(
            operation_id=str(uuid.uuid4()),
            operation_type=operation_type,
            table_or_collection=table_or_collection,
            timestamp=start_time,
            duration_ms=duration_ms,
            success=success,
            error_message=error_message,
            affected_records=affected_records
        )
    
    def handle_connection_error(self, error: Exception) -> bool:
        """Handle connection errors and determine if retry is appropriate"""
        # Common connection error handling logic
        connection_errors = [
            'connection', 'timeout', 'network', 'unreachable', 
            'refused', 'reset', 'closed', 'broken'
        ]
        
        error_str = str(error).lower()
        return any(err_type in error_str for err_type in connection_errors)
