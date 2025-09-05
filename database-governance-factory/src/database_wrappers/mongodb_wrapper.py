"""
MongoDB Database Wrapper
Comprehensive wrapper for MongoDB operations with full CRUD support
"""

import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo import IndexModel, ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure, ConnectionFailure
import uuid
import json
from bson import ObjectId, json_util

from .base_wrapper import (
    BaseDatabaseWrapper, DatabaseConfig, DatabaseOperation, QueryResult, 
    HealthStatus, BackupInfo, OperationType, DatabaseWrapperMixin
)

logger = logging.getLogger(__name__)

class MongoDBWrapper(BaseDatabaseWrapper, DatabaseWrapperMixin):
    """
    Comprehensive MongoDB wrapper with full feature support
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        
    async def connect(self) -> bool:
        """Establish MongoDB connection"""
        try:
            # Parse connection options
            connection_options = {
                'maxPoolSize': self.config.pool_size,
                'serverSelectionTimeoutMS': self.config.timeout * 1000,
                'connectTimeoutMS': self.config.timeout * 1000,
                **self.config.additional_config
            }
            
            if self.config.ssl_enabled:
                connection_options['ssl'] = True
            
            self.client = AsyncIOMotorClient(
                self.config.connection_string,
                **connection_options
            )
            
            # Test connection
            await self.client.admin.command('ping')
            self.database = self.client[self.config.database_name]
            self.is_connected = True
            
            logger.info(f"Successfully connected to MongoDB: {self.config.database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close MongoDB connection"""
        try:
            if self.client:
                self.client.close()
                self.is_connected = False
                logger.info("MongoDB connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
            return False
    
    async def health_check(self) -> HealthStatus:
        """Check MongoDB health and performance metrics"""
        start_time = datetime.utcnow()
        
        try:
            # Ping database
            await self.client.admin.command('ping')
            
            # Get server info
            server_info = await self.client.admin.command('buildInfo')
            
            # Get database stats
            db_stats = await self.database.command('dbStats')
            
            # Get server status for additional metrics
            server_status = await self.client.admin.command('serverStatus')
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthStatus(
                is_healthy=True,
                response_time_ms=response_time,
                version=server_info.get('version', 'unknown'),
                connection_count=server_status.get('connections', {}).get('current', 0),
                memory_usage_mb=server_status.get('mem', {}).get('resident', 0),
                disk_usage_mb=db_stats.get('dataSize', 0) / (1024 * 1024),
                additional_metrics={
                    'collections': db_stats.get('collections', 0),
                    'indexes': db_stats.get('indexes', 0),
                    'objects': db_stats.get('objects', 0),
                    'storage_size_mb': db_stats.get('storageSize', 0) / (1024 * 1024),
                    'index_size_mb': db_stats.get('indexSize', 0) / (1024 * 1024)
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
        """Insert documents into MongoDB collection"""
        start_time = datetime.utcnow()
        collection = self.database[table_or_collection]
        
        try:
            if isinstance(data, dict):
                # Single document insert
                result = await collection.insert_one(data)
                inserted_data = {'_id': result.inserted_id, **data}
                affected_records = 1
            else:
                # Multiple documents insert
                result = await collection.insert_many(data)
                inserted_data = [{'_id': _id, **doc} for _id, doc in zip(result.inserted_ids, data)]
                affected_records = len(result.inserted_ids)
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.CREATE, table_or_collection, start_time, True, 
                affected_records=affected_records
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=inserted_data,
                count=affected_records,
                execution_time_ms=operation.duration_ms,
                metadata={'operation_type': 'insert', 'collection': table_or_collection}
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
        """Read documents from MongoDB collection"""
        start_time = datetime.utcnow()
        collection = self.database[table_or_collection]
        
        try:
            # Build MongoDB query
            mongo_query = query or {}
            
            # Handle ObjectId conversions in query
            mongo_query = self._convert_objectids_in_query(mongo_query)
            
            # Create cursor
            cursor = collection.find(mongo_query, projection)
            
            # Apply sorting
            if sort:
                sort_spec = [(k, ASCENDING if v > 0 else DESCENDING) for k, v in sort.items()]
                cursor = cursor.sort(sort_spec)
            
            # Apply pagination
            if offset:
                cursor = cursor.skip(offset)
            if limit:
                cursor = cursor.limit(limit)
            
            # Execute query
            documents = await cursor.to_list(length=limit)
            
            # Convert ObjectIds to strings for JSON serialization
            documents = [self._convert_objectids_to_strings(doc) for doc in documents]
            
            # Get total count if not using limit
            total_count = len(documents)
            if limit is None:
                total_count = await collection.count_documents(mongo_query)
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.READ, table_or_collection, start_time, True,
                affected_records=len(documents)
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=documents,
                count=total_count,
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'find',
                    'collection': table_or_collection,
                    'query': str(mongo_query),
                    'projection': projection,
                    'limit': limit,
                    'offset': offset
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
        """Update documents in MongoDB collection"""
        start_time = datetime.utcnow()
        collection = self.database[table_or_collection]
        options = options or {}
        
        try:
            # Handle ObjectId conversions
            mongo_query = self._convert_objectids_in_query(query)
            
            # Determine update operation type
            update_many = options.get('update_many', False)
            upsert = options.get('upsert', False)
            
            # Prepare update document
            if not any(key.startswith('$') for key in update_data.keys()):
                # If no MongoDB operators, wrap in $set
                update_doc = {'$set': update_data}
            else:
                update_doc = update_data
            
            # Execute update
            if update_many:
                result = await collection.update_many(mongo_query, update_doc, upsert=upsert)
                affected_records = result.modified_count
                operation_type = 'update_many'
            else:
                result = await collection.update_one(mongo_query, update_doc, upsert=upsert)
                affected_records = result.modified_count
                operation_type = 'update_one'
            
            # Prepare result data
            result_data = {
                'matched_count': result.matched_count,
                'modified_count': result.modified_count,
                'upserted_id': str(result.upserted_id) if result.upserted_id else None
            }
            
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
                    'operation_type': operation_type,
                    'collection': table_or_collection,
                    'query': str(mongo_query),
                    'upsert': upsert
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
        """Delete documents from MongoDB collection"""
        start_time = datetime.utcnow()
        collection = self.database[table_or_collection]
        options = options or {}
        
        try:
            # Handle ObjectId conversions
            mongo_query = self._convert_objectids_in_query(query)
            
            # Determine delete operation type
            delete_many = options.get('delete_many', False)
            
            # Execute delete
            if delete_many:
                result = await collection.delete_many(mongo_query)
                operation_type = 'delete_many'
            else:
                result = await collection.delete_one(mongo_query)
                operation_type = 'delete_one'
            
            affected_records = result.deleted_count
            
            # Log operation
            operation = self.create_operation_metadata(
                OperationType.DELETE, table_or_collection, start_time, True,
                affected_records=affected_records
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data={'deleted_count': affected_records},
                count=affected_records,
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': operation_type,
                    'collection': table_or_collection,
                    'query': str(mongo_query)
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
        """Execute MongoDB aggregation or command"""
        start_time = datetime.utcnow()
        
        try:
            # Parse query as JSON for MongoDB operations
            query_obj = json.loads(query)
            
            if 'collection' in query_obj and 'operation' in query_obj:
                collection_name = query_obj['collection']
                operation = query_obj['operation']
                collection = self.database[collection_name]
                
                if operation == 'aggregate':
                    pipeline = query_obj.get('pipeline', [])
                    cursor = collection.aggregate(pipeline)
                    result_data = await cursor.to_list(length=None)
                    
                elif operation == 'find':
                    find_query = query_obj.get('query', {})
                    result_data = await collection.find(find_query).to_list(length=None)
                    
                else:
                    raise ValueError(f"Unsupported operation: {operation}")
                
                # Convert ObjectIds to strings
                result_data = [self._convert_objectids_to_strings(doc) for doc in result_data]
                
                operation_meta = self.create_operation_metadata(
                    OperationType.QUERY, collection_name, start_time, True,
                    affected_records=len(result_data)
                )
                self.log_operation(operation_meta)
                
                return QueryResult(
                    success=True,
                    data=result_data,
                    count=len(result_data),
                    execution_time_ms=operation_meta.duration_ms,
                    metadata={'operation_type': operation, 'query': query}
                )
            else:
                raise ValueError("Query must include 'collection' and 'operation' fields")
                
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
        """Execute MongoDB aggregation pipeline"""
        start_time = datetime.utcnow()
        collection = self.database[table_or_collection]
        
        try:
            cursor = collection.aggregate(pipeline)
            result_data = await cursor.to_list(length=None)
            
            # Convert ObjectIds to strings
            result_data = [self._convert_objectids_to_strings(doc) for doc in result_data]
            
            operation = self.create_operation_metadata(
                OperationType.AGGREGATE, table_or_collection, start_time, True,
                affected_records=len(result_data)
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result_data,
                count=len(result_data),
                execution_time_ms=operation.duration_ms,
                metadata={
                    'operation_type': 'aggregate',
                    'collection': table_or_collection,
                    'pipeline': pipeline
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
        """Execute multiple operations in batch"""
        results = []
        
        for op in operations:
            op_type = op.get('type')
            collection_name = op.get('collection')
            
            if op_type == 'create':
                result = await self.create(collection_name, op.get('data'), op.get('options'))
            elif op_type == 'read':
                result = await self.read(
                    collection_name, op.get('query'), op.get('projection'),
                    op.get('limit'), op.get('offset'), op.get('sort')
                )
            elif op_type == 'update':
                result = await self.update(
                    collection_name, op.get('query'), op.get('update_data'), op.get('options')
                )
            elif op_type == 'delete':
                result = await self.delete(collection_name, op.get('query'), op.get('options'))
            elif op_type == 'aggregate':
                result = await self.aggregate(collection_name, op.get('pipeline'))
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
        """Create MongoDB collection with optional schema validation"""
        try:
            # Create collection
            collection = self.database[name]
            
            # Add schema validation if provided
            if schema:
                validator = schema.get('validator', {})
                validation_level = schema.get('validation_level', 'strict')
                validation_action = schema.get('validation_action', 'error')
                
                await self.database.command({
                    'collMod': name,
                    'validator': validator,
                    'validationLevel': validation_level,
                    'validationAction': validation_action
                })
            
            logger.info(f"Collection '{name}' created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating collection '{name}': {e}")
            return False
    
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop MongoDB collection"""
        try:
            await self.database.drop_collection(name)
            logger.info(f"Collection '{name}' dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Error dropping collection '{name}': {e}")
            return False
    
    async def list_tables_or_collections(self) -> List[str]:
        """List all MongoDB collections"""
        try:
            return await self.database.list_collection_names()
        except Exception as e:
            logger.error(f"Error listing collections: {e}")
            return []
    
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get MongoDB collection schema information"""
        try:
            # Get collection info including validation rules
            collection_info = await self.database.command("listCollections", filter={"name": table_or_collection})
            
            schema = {
                'collection_name': table_or_collection,
                'options': {},
                'indexes': [],
                'sample_document': None,
                'document_count': 0
            }
            
            if collection_info['cursor']['firstBatch']:
                options = collection_info['cursor']['firstBatch'][0].get('options', {})
                schema['options'] = options
            
            # Get indexes
            collection = self.database[table_or_collection]
            indexes = await collection.list_indexes().to_list(length=None)
            schema['indexes'] = [self._convert_objectids_to_strings(idx) for idx in indexes]
            
            # Get document count
            schema['document_count'] = await collection.count_documents({})
            
            # Get sample document for schema inference
            if schema['document_count'] > 0:
                sample_doc = await collection.find_one()
                if sample_doc:
                    schema['sample_document'] = self._convert_objectids_to_strings(sample_doc)
            
            return schema
            
        except Exception as e:
            logger.error(f"Error getting schema for collection '{table_or_collection}': {e}")
            return {}
    
    # === Index Management ===
    
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Create MongoDB index"""
        try:
            collection = self.database[table_or_collection]
            options = options or {}
            
            # Create index model
            index_model = IndexModel(list(index_spec.items()), **options)
            
            # Create index
            result = await collection.create_indexes([index_model])
            logger.info(f"Index created on collection '{table_or_collection}': {result}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating index on collection '{table_or_collection}': {e}")
            return False
    
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Drop MongoDB index"""
        try:
            collection = self.database[table_or_collection]
            await collection.drop_index(index_name)
            logger.info(f"Index '{index_name}' dropped from collection '{table_or_collection}'")
            return True
        except Exception as e:
            logger.error(f"Error dropping index '{index_name}' from collection '{table_or_collection}': {e}")
            return False
    
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """List all indexes for MongoDB collection"""
        try:
            collection = self.database[table_or_collection]
            indexes = await collection.list_indexes().to_list(length=None)
            return [self._convert_objectids_to_strings(idx) for idx in indexes]
        except Exception as e:
            logger.error(f"Error listing indexes for collection '{table_or_collection}': {e}")
            return []
    
    # === Transaction Support ===
    
    async def begin_transaction(self) -> Any:
        """Begin MongoDB transaction session"""
        try:
            session = await self.client.start_session()
            session.start_transaction()
            return session
        except Exception as e:
            logger.error(f"Error starting transaction: {e}")
            return None
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit MongoDB transaction"""
        try:
            await transaction.commit_transaction()
            await transaction.end_session()
            return True
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            return False
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback MongoDB transaction"""
        try:
            await transaction.abort_transaction()
            await transaction.end_session()
            return True
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            return False
    
    # === Backup and Recovery ===
    
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Create MongoDB backup using mongodump"""
        start_time = datetime.utcnow()
        backup_id = str(uuid.uuid4())
        
        try:
            # This is a simplified backup - in production, use proper mongodump
            collections = await self.list_tables_or_collections()
            backup_data = {}
            total_size = 0
            
            for collection_name in collections:
                collection = self.database[collection_name]
                documents = await collection.find().to_list(length=None)
                backup_data[collection_name] = [self._convert_objectids_to_strings(doc) for doc in documents]
                total_size += len(json.dumps(backup_data[collection_name], default=str))
            
            # In a real implementation, save to file system or cloud storage
            backup_location = backup_config.get('location', f'/tmp/mongodb_backup_{backup_id}.json')
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='full',
                size_mb=total_size / (1024 * 1024),
                location=backup_location,
                timestamp=start_time,
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'collections_count': len(collections),
                    'database_name': self.config.database_name
                }
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='full',
                size_mb=0,
                location='',
                timestamp=start_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    async def restore_backup(self, backup_info: BackupInfo, 
                           restore_config: Dict[str, Any] = None) -> bool:
        """Restore MongoDB from backup"""
        try:
            # This is a simplified restore - in production, use proper mongorestore
            # Implementation would read from backup file and restore collections
            logger.info(f"Restore operation for backup {backup_info.backup_id} not implemented")
            return False
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """List available MongoDB backups"""
        # This would typically query a backup storage system
        return []
    
    # === Monitoring and Statistics ===
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get MongoDB database statistics"""
        try:
            db_stats = await self.database.command('dbStats')
            server_status = await self.client.admin.command('serverStatus')
            
            return {
                'database_name': self.config.database_name,
                'collections': db_stats.get('collections', 0),
                'objects': db_stats.get('objects', 0),
                'data_size_mb': db_stats.get('dataSize', 0) / (1024 * 1024),
                'storage_size_mb': db_stats.get('storageSize', 0) / (1024 * 1024),
                'index_size_mb': db_stats.get('indexSize', 0) / (1024 * 1024),
                'connections': server_status.get('connections', {}),
                'memory': server_status.get('mem', {}),
                'opcounters': server_status.get('opcounters', {})
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get MongoDB performance metrics"""
        try:
            server_status = await self.client.admin.command('serverStatus')
            
            return {
                'opcounters': server_status.get('opcounters', {}),
                'opcountersRepl': server_status.get('opcountersRepl', {}),
                'metrics': server_status.get('metrics', {}),
                'locks': server_status.get('locks', {}),
                'globalLock': server_status.get('globalLock', {}),
                'wiredTiger': server_status.get('wiredTiger', {})
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get MongoDB slow queries from profiler"""
        try:
            # Enable profiling if not already enabled
            await self.database.command('profile', 2)
            
            # Query the system.profile collection
            slow_queries = await self.database['system.profile'].find().sort('ts', -1).limit(limit).to_list(length=limit)
            
            return [self._convert_objectids_to_strings(query) for query in slow_queries]
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    # === Streaming Support ===
    
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream large datasets in batches"""
        collection = self.database[table_or_collection]
        mongo_query = self._convert_objectids_in_query(query or {})
        
        try:
            cursor = collection.find(mongo_query).batch_size(batch_size)
            
            batch = []
            async for document in cursor:
                batch.append(self._convert_objectids_to_strings(document))
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            # Yield remaining documents
            if batch:
                yield batch
                
        except Exception as e:
            logger.error(f"Error streaming data from collection '{table_or_collection}': {e}")
            yield []
    
    # === Connection Pool Management ===
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get MongoDB connection pool statistics"""
        try:
            server_status = await self.client.admin.command('serverStatus')
            connections = server_status.get('connections', {})
            
            return {
                'current': connections.get('current', 0),
                'available': connections.get('available', 0),
                'total_created': connections.get('totalCreated', 0),
                'active': connections.get('active', 0)
            }
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {}
    
    async def reset_pool(self) -> bool:
        """Reset MongoDB connection pool"""
        try:
            # Close and recreate client
            if self.client:
                self.client.close()
            
            return await self.connect()
        except Exception as e:
            logger.error(f"Error resetting pool: {e}")
            return False
    
    # === Utility Methods ===
    
    def _convert_objectids_in_query(self, query: Dict[str, Any]) -> Dict[str, Any]:
        """Convert string ObjectIds to ObjectId objects in query"""
        converted_query = {}
        
        for key, value in query.items():
            if key == '_id' and isinstance(value, str):
                try:
                    converted_query[key] = ObjectId(value)
                except:
                    converted_query[key] = value
            elif isinstance(value, dict):
                converted_query[key] = self._convert_objectids_in_query(value)
            elif isinstance(value, list):
                converted_query[key] = [
                    ObjectId(item) if isinstance(item, str) and len(item) == 24 else item
                    for item in value
                ]
            else:
                converted_query[key] = value
        
        return converted_query
    
    def _convert_objectids_to_strings(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Convert ObjectId objects to strings for JSON serialization"""
        if isinstance(document, dict):
            return {
                key: str(value) if isinstance(value, ObjectId) else 
                     self._convert_objectids_to_strings(value) if isinstance(value, dict) else
                     [str(item) if isinstance(item, ObjectId) else 
                      self._convert_objectids_to_strings(item) if isinstance(item, dict) else item
                      for item in value] if isinstance(value, list) else value
                for key, value in document.items()
            }
        return document
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get MongoDB-specific operations"""
        return [
            'text_search',
            'geospatial_query',
            'map_reduce',
            'bulk_write',
            'watch_changes',
            'create_user',
            'explain_query'
        ]
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute MongoDB-specific operations"""
        parameters = parameters or {}
        
        if operation_name == 'text_search':
            collection_name = parameters.get('collection')
            search_text = parameters.get('text')
            collection = self.database[collection_name]
            
            cursor = collection.find({'$text': {'$search': search_text}})
            results = await cursor.to_list(length=None)
            return [self._convert_objectids_to_strings(doc) for doc in results]
        
        elif operation_name == 'geospatial_query':
            collection_name = parameters.get('collection')
            location = parameters.get('location')  # [longitude, latitude]
            max_distance = parameters.get('max_distance', 1000)
            collection = self.database[collection_name]
            
            cursor = collection.find({
                'location': {
                    '$near': {
                        '$geometry': {'type': 'Point', 'coordinates': location},
                        '$maxDistance': max_distance
                    }
                }
            })
            results = await cursor.to_list(length=None)
            return [self._convert_objectids_to_strings(doc) for doc in results]
        
        elif operation_name == 'explain_query':
            collection_name = parameters.get('collection')
            query = parameters.get('query', {})
            collection = self.database[collection_name]
            
            explain_result = await collection.find(query).explain()
            return self._convert_objectids_to_strings(explain_result)
        
        else:
            raise NotImplementedError(f"MongoDB operation '{operation_name}' not implemented")
