"""
Azure Cosmos DB Wrapper
Comprehensive wrapper for Azure Cosmos DB operations with SQL API support
"""

import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
import json
import uuid

try:
    from azure.cosmos.aio import CosmosClient, DatabaseProxy, ContainerProxy
    from azure.cosmos import PartitionKey, exceptions
except ImportError:
    CosmosClient = None
    DatabaseProxy = None
    ContainerProxy = None
    exceptions = None

from .base_wrapper import (
    BaseDatabaseWrapper, DatabaseConfig, DatabaseOperation, QueryResult, 
    HealthStatus, BackupInfo, OperationType, DatabaseWrapperMixin
)

logger = logging.getLogger(__name__)

class CosmosDBWrapper(BaseDatabaseWrapper, DatabaseWrapperMixin):
    """
    Comprehensive Azure Cosmos DB wrapper with SQL API support
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.cosmos_client: Optional[CosmosClient] = None
        self.database: Optional[DatabaseProxy] = None
        
    async def connect(self) -> bool:
        """Establish Cosmos DB connection"""
        try:
            if not CosmosClient:
                raise ImportError("azure-cosmos package is required for Cosmos DB operations")
            
            # Parse connection string
            # Format: AccountEndpoint=https://...;AccountKey=...;
            connection_parts = {}
            for part in self.config.connection_string.split(';'):
                if '=' in part:
                    key, value = part.split('=', 1)
                    connection_parts[key] = value
            
            endpoint = connection_parts.get('AccountEndpoint')
            key = connection_parts.get('AccountKey')
            
            if not endpoint or not key:
                raise ValueError("Invalid Cosmos DB connection string")
            
            # Create client
            self.cosmos_client = CosmosClient(
                endpoint,
                key,
                **self.config.additional_config
            )
            
            # Get or create database
            self.database = self.cosmos_client.get_database_client(self.config.database_name)
            
            # Test connection
            await self.database.read()
            
            self.is_connected = True
            logger.info(f"Successfully connected to Cosmos DB: {self.config.database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Cosmos DB: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close Cosmos DB connection"""
        try:
            if self.cosmos_client:
                await self.cosmos_client.close()
                self.is_connected = False
                logger.info("Cosmos DB connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing Cosmos DB connection: {e}")
            return False
    
    async def health_check(self) -> HealthStatus:
        """Check Cosmos DB health and metrics"""
        start_time = datetime.utcnow()
        
        try:
            # Read database properties
            db_properties = await self.database.read()
            
            # Get account information
            account_info = await self.cosmos_client.get_database_account()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthStatus(
                is_healthy=True,
                response_time_ms=response_time,
                version='Cosmos DB SQL API',
                additional_metrics={
                    'database_id': db_properties.get('id'),
                    'account_name': account_info.DatabasesLink.split('/')[-2],
                    'consistency_level': account_info.ConsistencyPolicy.get('defaultConsistencyLevel'),
                    'regions': [region.name for region in account_info.ReadableLocations]
                }
            )
            
        except Exception as e:
            return HealthStatus(
                is_healthy=False,
                response_time_ms=(datetime.utcnow() - start_time).total_seconds() * 1000,
                version='unknown',
                error_message=str(e)
            )
    
    # === CRUD Operations ===
    
    async def create(self, table_or_collection: str, data: Union[Dict, List[Dict]], 
                    options: Dict[str, Any] = None) -> QueryResult:
        """Create documents in Cosmos DB container"""
        start_time = datetime.utcnow()
        
        try:
            container = self.database.get_container_client(table_or_collection)
            
            if isinstance(data, dict):
                # Single document create
                if 'id' not in data:
                    data['id'] = str(uuid.uuid4())
                
                response = await container.create_item(data)
                result_data = response
                affected_records = 1
                
            else:
                # Multiple documents create
                results = []
                for item in data:
                    if 'id' not in item:
                        item['id'] = str(uuid.uuid4())
                    
                    response = await container.create_item(item)
                    results.append(response)
                
                result_data = results
                affected_records = len(results)
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.CREATE, table_or_collection, start_time, True,
                affected_records=affected_records
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result_data,
                count=affected_records,
                execution_time_ms=operation.duration_ms,
                metadata={'operation_type': 'create_item', 'container': table_or_collection}
            )
            
        except Exception as e:
            error_msg = self.format_error_message('create', e)
            operation = self.create_operation_metadata(
                OperationType.CREATE, table_or_collection, start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def read(self, table_or_collection: str, query: Dict[str, Any] = None,
                  projection: Dict[str, Any] = None, limit: int = None, 
                  offset: int = None, sort: Dict[str, Any] = None) -> QueryResult:
        """Read documents from Cosmos DB container"""
        start_time = datetime.utcnow()
        
        try:
            container = self.database.get_container_client(table_or_collection)
            
            if query and 'id' in query and 'partition_key' in query:
                # Point read (most efficient)
                try:
                    response = await container.read_item(
                        item=query['id'],
                        partition_key=query['partition_key']
                    )
                    result_data = [response]
                    count = 1
                except exceptions.CosmosResourceNotFoundError:
                    result_data = []
                    count = 0
            
            else:
                # Query documents
                sql_query = self._build_cosmos_query(query, projection, sort, limit, offset)
                
                items = []
                async for item in container.query_items(
                    query=sql_query,
                    enable_cross_partition_query=True
                ):
                    items.append(item)
                
                result_data = items
                count = len(items)
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.READ, table_or_collection, start_time, True,
                affected_records=count
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result_data,
                count=count,
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'query_items',
                    'container': table_or_collection,
                    'query': str(query)
                }
            )
            
        except Exception as e:
            error_msg = self.format_error_message('read', e)
            operation = self.create_operation_metadata(
                OperationType.READ, table_or_collection, start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def update(self, table_or_collection: str, query: Dict[str, Any],
                    update_data: Dict[str, Any], options: Dict[str, Any] = None) -> QueryResult:
        """Update documents in Cosmos DB container"""
        start_time = datetime.utcnow()
        options = options or {}
        
        try:
            container = self.database.get_container_client(table_or_collection)
            
            if 'id' in query and 'partition_key' in query:
                # Point update
                try:
                    # Read current item
                    current_item = await container.read_item(
                        item=query['id'],
                        partition_key=query['partition_key']
                    )
                    
                    # Apply updates
                    for key, value in update_data.items():
                        current_item[key] = value
                    
                    # Replace item
                    response = await container.replace_item(
                        item=current_item['id'],
                        body=current_item
                    )
                    
                    result_data = [response]
                    affected_records = 1
                    
                except exceptions.CosmosResourceNotFoundError:
                    if options.get('upsert', False):
                        # Create new item
                        new_item = {**query, **update_data}
                        if 'id' not in new_item:
                            new_item['id'] = str(uuid.uuid4())
                        
                        response = await container.create_item(new_item)
                        result_data = [response]
                        affected_records = 1
                    else:
                        result_data = []
                        affected_records = 0
            
            else:
                # Query and update multiple items
                sql_query = self._build_cosmos_query(query)
                
                items_to_update = []
                async for item in container.query_items(
                    query=sql_query,
                    enable_cross_partition_query=True
                ):
                    items_to_update.append(item)
                
                updated_items = []
                for item in items_to_update:
                    # Apply updates
                    for key, value in update_data.items():
                        item[key] = value
                    
                    # Replace item
                    response = await container.replace_item(
                        item=item['id'],
                        body=item
                    )
                    updated_items.append(response)
                
                result_data = updated_items
                affected_records = len(updated_items)
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.UPDATE, table_or_collection, start_time, True,
                affected_records=affected_records
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result_data,
                count=affected_records,
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'replace_item',
                    'container': table_or_collection,
                    'query': str(query)
                }
            )
            
        except Exception as e:
            error_msg = self.format_error_message('update', e)
            operation = self.create_operation_metadata(
                OperationType.UPDATE, table_or_collection, start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def delete(self, table_or_collection: str, query: Dict[str, Any],
                    options: Dict[str, Any] = None) -> QueryResult:
        """Delete documents from Cosmos DB container"""
        start_time = datetime.utcnow()
        
        try:
            container = self.database.get_container_client(table_or_collection)
            
            if 'id' in query and 'partition_key' in query:
                # Point delete
                try:
                    await container.delete_item(
                        item=query['id'],
                        partition_key=query['partition_key']
                    )
                    result_data = [{'id': query['id'], 'deleted': True}]
                    affected_records = 1
                    
                except exceptions.CosmosResourceNotFoundError:
                    result_data = [{'id': query['id'], 'deleted': False, 'reason': 'Not found'}]
                    affected_records = 0
            
            else:
                # Query and delete multiple items
                sql_query = self._build_cosmos_query(query)
                
                items_to_delete = []
                async for item in container.query_items(
                    query=sql_query,
                    enable_cross_partition_query=True
                ):
                    items_to_delete.append(item)
                
                deleted_items = []
                for item in items_to_delete:
                    try:
                        await container.delete_item(
                            item=item['id'],
                            partition_key=item.get(container.partition_key.replace('/', ''))
                        )
                        deleted_items.append({'id': item['id'], 'deleted': True})
                    except Exception as delete_error:
                        deleted_items.append({
                            'id': item['id'], 
                            'deleted': False, 
                            'error': str(delete_error)
                        })
                
                result_data = deleted_items
                affected_records = len([item for item in deleted_items if item['deleted']])
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.DELETE, table_or_collection, start_time, True,
                affected_records=affected_records
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result_data,
                count=affected_records,
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'delete_item',
                    'container': table_or_collection,
                    'query': str(query)
                }
            )
            
        except Exception as e:
            error_msg = self.format_error_message('delete', e)
            operation = self.create_operation_metadata(
                OperationType.DELETE, table_or_collection, start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    # === Advanced Query Operations ===
    
    async def query(self, query: str, parameters: List[Any] = None) -> QueryResult:
        """Execute SQL query on Cosmos DB"""
        start_time = datetime.utcnow()
        
        try:
            # Parse container from query if possible
            container_name = self._extract_container_from_query(query)
            container = self.database.get_container_client(container_name)
            
            # Execute query
            items = []
            async for item in container.query_items(
                query=query,
                parameters=parameters or [],
                enable_cross_partition_query=True
            ):
                items.append(item)
            
            operation = self.create_operation_metadata(
                OperationType.QUERY, container_name, start_time, True,
                affected_records=len(items)
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=items,
                count=len(items),
                execution_time_ms=operation.duration_ms,
                metadata={'operation_type': 'sql_query', 'sql': query}
            )
            
        except Exception as e:
            error_msg = self.format_error_message('query', e)
            operation = self.create_operation_metadata(
                OperationType.QUERY, 'unknown', start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def aggregate(self, table_or_collection: str, pipeline: List[Dict[str, Any]]) -> QueryResult:
        """Execute aggregation on Cosmos DB (converted to SQL)"""
        start_time = datetime.utcnow()
        
        try:
            # Convert MongoDB-style pipeline to Cosmos DB SQL
            sql_query = self._convert_pipeline_to_cosmos_sql(table_or_collection, pipeline)
            
            container = self.database.get_container_client(table_or_collection)
            
            items = []
            async for item in container.query_items(
                query=sql_query,
                enable_cross_partition_query=True
            ):
                items.append(item)
            
            operation = self.create_operation_metadata(
                OperationType.AGGREGATE, table_or_collection, start_time, True,
                affected_records=len(items)
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=items,
                count=len(items),
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'aggregate',
                    'container': table_or_collection,
                    'pipeline': pipeline,
                    'sql': sql_query
                }
            )
            
        except Exception as e:
            error_msg = self.format_error_message('aggregate', e)
            operation = self.create_operation_metadata(
                OperationType.AGGREGATE, table_or_collection, start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def batch_operation(self, operations: List[Dict[str, Any]]) -> List[QueryResult]:
        """Execute multiple operations (Cosmos DB doesn't have true batch transactions across partitions)"""
        results = []
        
        for op in operations:
            op_type = op.get('type')
            container_name = op.get('container')
            
            if op_type == 'create':
                result = await self.create(container_name, op.get('data'), op.get('options'))
            elif op_type == 'read':
                result = await self.read(
                    container_name, op.get('query'), op.get('projection'),
                    op.get('limit'), op.get('offset'), op.get('sort')
                )
            elif op_type == 'update':
                result = await self.update(
                    container_name, op.get('query'), op.get('update_data'), op.get('options')
                )
            elif op_type == 'delete':
                result = await self.delete(container_name, op.get('query'), op.get('options'))
            else:
                result = QueryResult(
                    success=False,
                    data=None,
                    error_message=f"Unsupported operation type: {op_type}"
                )
            
            results.append(result)
        
        return results
    
    # === Schema Management ===
    
    async def create_table_or_collection(self, name: str, schema: Dict[str, Any] = None) -> bool:
        """Create Cosmos DB container"""
        try:
            partition_key = schema.get('partition_key', '/id') if schema else '/id'
            
            container_config = {
                'id': name,
                'partition_key': PartitionKey(path=partition_key)
            }
            
            if schema:
                if 'throughput' in schema:
                    container_config['offer_throughput'] = schema['throughput']
                if 'unique_key_policy' in schema:
                    container_config['unique_key_policy'] = schema['unique_key_policy']
                if 'indexing_policy' in schema:
                    container_config['indexing_policy'] = schema['indexing_policy']
            
            await self.database.create_container(**container_config)
            logger.info(f"Cosmos DB container '{name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating Cosmos DB container '{name}': {e}")
            return False
    
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop Cosmos DB container"""
        try:
            container = self.database.get_container_client(name)
            await container.delete_container()
            logger.info(f"Cosmos DB container '{name}' dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Error dropping Cosmos DB container '{name}': {e}")
            return False
    
    async def list_tables_or_collections(self) -> List[str]:
        """List all Cosmos DB containers"""
        try:
            containers = []
            async for container in self.database.list_containers():
                containers.append(container['id'])
            return containers
        except Exception as e:
            logger.error(f"Error listing Cosmos DB containers: {e}")
            return []
    
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get Cosmos DB container schema information"""
        try:
            container = self.database.get_container_client(table_or_collection)
            container_properties = await container.read()
            
            return {
                'container_id': container_properties.get('id'),
                'partition_key': container_properties.get('partitionKey'),
                'indexing_policy': container_properties.get('indexingPolicy'),
                'unique_key_policy': container_properties.get('uniqueKeyPolicy'),
                'conflict_resolution_policy': container_properties.get('conflictResolutionPolicy'),
                'created_time': container_properties.get('_ts'),
                'etag': container_properties.get('_etag')
            }
        except Exception as e:
            logger.error(f"Error getting schema for container '{table_or_collection}': {e}")
            return {}
    
    # === Index Management ===
    
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Update Cosmos DB container indexing policy"""
        try:
            container = self.database.get_container_client(table_or_collection)
            current_properties = await container.read()
            
            # Update indexing policy
            indexing_policy = current_properties.get('indexingPolicy', {})
            
            if 'included_paths' in index_spec:
                indexing_policy['includedPaths'] = index_spec['included_paths']
            if 'excluded_paths' in index_spec:
                indexing_policy['excludedPaths'] = index_spec['excluded_paths']
            if 'composite_indexes' in index_spec:
                indexing_policy['compositeIndexes'] = index_spec['composite_indexes']
            
            # Replace container with updated indexing policy
            current_properties['indexingPolicy'] = indexing_policy
            await container.replace_container(current_properties)
            
            logger.info(f"Indexing policy updated for container '{table_or_collection}'")
            return True
        except Exception as e:
            logger.error(f"Error updating indexing policy for container '{table_or_collection}': {e}")
            return False
    
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Remove specific paths from indexing policy"""
        try:
            # Cosmos DB doesn't have named indexes like traditional databases
            # This would require removing specific paths from indexing policy
            logger.warning("Cosmos DB doesn't support dropping individual indexes")
            return False
        except Exception as e:
            logger.error(f"Error dropping index '{index_name}': {e}")
            return False
    
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """List indexing policy for Cosmos DB container"""
        try:
            container = self.database.get_container_client(table_or_collection)
            properties = await container.read()
            
            indexing_policy = properties.get('indexingPolicy', {})
            return [indexing_policy]
        except Exception as e:
            logger.error(f"Error listing indexes for container '{table_or_collection}': {e}")
            return []
    
    # === Transaction Support ===
    
    async def begin_transaction(self) -> Any:
        """Cosmos DB doesn't support multi-document transactions across partitions"""
        logger.warning("Cosmos DB doesn't support traditional transactions across partitions")
        return None
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Cosmos DB doesn't support traditional transactions"""
        return False
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Cosmos DB doesn't support traditional transactions"""
        return False
    
    # === Backup and Recovery ===
    
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Cosmos DB backup (continuous backup is handled by Azure)"""
        start_time = datetime.utcnow()
        backup_id = str(uuid.uuid4())
        
        try:
            # Cosmos DB uses continuous backup - this is metadata only
            containers = await self.list_tables_or_collections()
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='continuous',
                size_mb=0,  # Azure manages this
                location='Azure Managed',
                timestamp=start_time,
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'backup_method': 'azure_continuous',
                    'containers_count': len(containers),
                    'database_name': self.config.database_name
                }
            )
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='continuous',
                size_mb=0,
                location='',
                timestamp=start_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    async def restore_backup(self, backup_info: BackupInfo, 
                           restore_config: Dict[str, Any] = None) -> bool:
        """Cosmos DB restore (handled through Azure portal/API)"""
        try:
            logger.info("Cosmos DB restore must be initiated through Azure portal or ARM templates")
            return False
        except Exception as e:
            logger.error(f"Error with Cosmos DB restore: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """Cosmos DB backups are managed by Azure"""
        return []
    
    # === Monitoring and Statistics ===
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get Cosmos DB statistics"""
        try:
            # Get database properties
            db_properties = await self.database.read()
            
            # Get containers and their statistics
            containers = []
            async for container_props in self.database.list_containers():
                containers.append(container_props)
            
            return {
                'database_id': db_properties.get('id'),
                'containers_count': len(containers),
                'containers': [container.get('id') for container in containers],
                'last_modified': db_properties.get('_ts')
            }
        except Exception as e:
            logger.error(f"Error getting Cosmos DB statistics: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get Cosmos DB performance metrics"""
        try:
            # Cosmos DB metrics are typically accessed through Azure Monitor
            return {
                'note': 'Performance metrics available through Azure Monitor',
                'request_units': 'Check Azure portal for RU consumption',
                'throughput': 'Configured at container or database level'
            }
        except Exception as e:
            logger.error(f"Error getting Cosmos DB performance metrics: {e}")
            return {}
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get slow queries (available through Azure diagnostics)"""
        try:
            return [{
                'note': 'Slow query information available through Azure Monitor and Diagnostic Settings',
                'recommendation': 'Enable diagnostic logs to track query performance'
            }]
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    # === Streaming Support ===
    
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream Cosmos DB data in batches"""
        try:
            container = self.database.get_container_client(table_or_collection)
            
            sql_query = self._build_cosmos_query(query)
            
            batch = []
            async for item in container.query_items(
                query=sql_query,
                enable_cross_partition_query=True
            ):
                batch.append(item)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            # Yield remaining items
            if batch:
                yield batch
                
        except Exception as e:
            logger.error(f"Error streaming data from container '{table_or_collection}': {e}")
            yield []
    
    # === Connection Pool Management ===
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Cosmos DB connection stats"""
        try:
            return {
                'connection_mode': 'Direct',
                'note': 'Cosmos DB uses connection pooling internally'
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {}
    
    async def reset_pool(self) -> bool:
        """Reset Cosmos DB connection"""
        try:
            await self.disconnect()
            return await self.connect()
        except Exception as e:
            logger.error(f"Error resetting Cosmos DB connection: {e}")
            return False
    
    # === Utility Methods ===
    
    def _build_cosmos_query(self, query: Dict[str, Any] = None, projection: Dict[str, Any] = None,
                           sort: Dict[str, Any] = None, limit: int = None, offset: int = None) -> str:
        """Build Cosmos DB SQL query from parameters"""
        # Build SELECT clause
        if projection:
            if isinstance(projection, dict):
                # MongoDB-style projection
                included_fields = [k for k, v in projection.items() if v == 1]
                if included_fields:
                    select_clause = ', '.join([f'c.{field}' for field in included_fields])
                else:
                    select_clause = '*'
            else:
                select_clause = ', '.join([f'c.{field}' for field in projection])
        else:
            select_clause = '*'
        
        sql_query = f"SELECT {select_clause} FROM c"
        
        # Build WHERE clause
        if query:
            where_conditions = []
            for field, value in query.items():
                if isinstance(value, dict):
                    # Handle operators
                    for op, op_value in value.items():
                        if op == '$gt':
                            where_conditions.append(f"c.{field} > {self._format_value(op_value)}")
                        elif op == '$gte':
                            where_conditions.append(f"c.{field} >= {self._format_value(op_value)}")
                        elif op == '$lt':
                            where_conditions.append(f"c.{field} < {self._format_value(op_value)}")
                        elif op == '$lte':
                            where_conditions.append(f"c.{field} <= {self._format_value(op_value)}")
                        elif op == '$ne':
                            where_conditions.append(f"c.{field} != {self._format_value(op_value)}")
                        elif op == '$in':
                            values = ', '.join([self._format_value(v) for v in op_value])
                            where_conditions.append(f"c.{field} IN ({values})")
                else:
                    where_conditions.append(f"c.{field} = {self._format_value(value)}")
            
            if where_conditions:
                sql_query += f" WHERE {' AND '.join(where_conditions)}"
        
        # Build ORDER BY clause
        if sort:
            order_parts = []
            for field, direction in sort.items():
                order_dir = 'ASC' if direction > 0 else 'DESC'
                order_parts.append(f"c.{field} {order_dir}")
            sql_query += f" ORDER BY {', '.join(order_parts)}"
        
        # Build OFFSET and LIMIT
        if offset:
            sql_query += f" OFFSET {offset}"
        if limit:
            sql_query += f" LIMIT {limit}"
        
        return sql_query
    
    def _format_value(self, value: Any) -> str:
        """Format value for Cosmos DB SQL query"""
        if isinstance(value, str):
            return f"'{value}'"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, bool):
            return 'true' if value else 'false'
        elif value is None:
            return 'null'
        else:
            return f"'{json.dumps(value)}'"
    
    def _extract_container_from_query(self, query: str) -> str:
        """Extract container name from SQL query"""
        # Basic extraction - look for FROM clause
        query_upper = query.upper()
        if 'FROM' in query_upper:
            parts = query_upper.split('FROM')[1].strip().split()
            if parts:
                return parts[0].replace('C', '').strip()
        
        return 'unknown'
    
    def _convert_pipeline_to_cosmos_sql(self, container: str, pipeline: List[Dict[str, Any]]) -> str:
        """Convert MongoDB-style pipeline to Cosmos DB SQL"""
        sql_query = "SELECT * FROM c"
        
        for stage in pipeline:
            if '$match' in stage:
                # Convert match to WHERE clause
                match_conditions = []
                for field, value in stage['$match'].items():
                    match_conditions.append(f"c.{field} = {self._format_value(value)}")
                
                if match_conditions:
                    sql_query += f" WHERE {' AND '.join(match_conditions)}"
            
            elif '$sort' in stage:
                # Convert sort to ORDER BY
                sort_parts = []
                for field, direction in stage['$sort'].items():
                    order_dir = 'ASC' if direction > 0 else 'DESC'
                    sort_parts.append(f"c.{field} {order_dir}")
                sql_query += f" ORDER BY {', '.join(sort_parts)}"
            
            elif '$limit' in stage:
                # Add LIMIT
                sql_query += f" LIMIT {stage['$limit']}"
            
            elif '$project' in stage:
                # Update SELECT clause
                projected_fields = []
                for field, include in stage['$project'].items():
                    if include == 1:
                        projected_fields.append(f"c.{field}")
                
                if projected_fields:
                    sql_query = sql_query.replace("SELECT *", f"SELECT {', '.join(projected_fields)}")
        
        return sql_query
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get Cosmos DB-specific operations"""
        return [
            'change_feed',
            'stored_procedure',
            'user_defined_function',
            'trigger',
            'conflict_resolution'
        ]
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute Cosmos DB-specific operations"""
        parameters = parameters or {}
        
        if operation_name == 'change_feed':
            container_name = parameters.get('container')
            container = self.database.get_container_client(container_name)
            
            # Read change feed
            changes = []
            async for change in container.read_change_feed():
                changes.append(change)
                if len(changes) >= 100:  # Limit to prevent large responses
                    break
            
            return changes
        
        elif operation_name == 'stored_procedure':
            container_name = parameters.get('container')
            proc_id = parameters.get('procedure_id')
            proc_params = parameters.get('parameters', [])
            
            container = self.database.get_container_client(container_name)
            result = await container.scripts.execute_stored_procedure(
                sproc=proc_id,
                params=proc_params
            )
            return result
        
        else:
            raise NotImplementedError(f"Cosmos DB operation '{operation_name}' not implemented")
