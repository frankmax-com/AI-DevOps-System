"""
Redis Database Wrapper
Comprehensive wrapper for Redis operations with full key-value support
"""

import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
import json
import uuid
import pickle
from urllib.parse import urlparse

try:
    import aioredis
    from aioredis import Redis
except ImportError:
    # Fallback for different aioredis versions
    try:
        import aioredis
        Redis = aioredis.Redis
    except:
        Redis = None

from .base_wrapper import (
    BaseDatabaseWrapper, DatabaseConfig, DatabaseOperation, QueryResult, 
    HealthStatus, BackupInfo, OperationType, DatabaseWrapperMixin
)

logger = logging.getLogger(__name__)

class RedisWrapper(BaseDatabaseWrapper, DatabaseWrapperMixin):
    """
    Comprehensive Redis wrapper with full key-value operations support
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.redis_client: Optional[Redis] = None
        
    async def connect(self) -> bool:
        """Establish Redis connection"""
        try:
            # Parse connection options
            connection_options = {
                'encoding': 'utf-8',
                'decode_responses': True,
                'socket_timeout': self.config.timeout,
                'socket_connect_timeout': self.config.timeout,
                **self.config.additional_config
            }
            
            if self.config.ssl_enabled:
                connection_options['ssl'] = True
            
            # Create Redis client
            self.redis_client = aioredis.from_url(
                self.config.connection_string,
                **connection_options
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            
            logger.info(f"Successfully connected to Redis: {self.config.database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close Redis connection"""
        try:
            if self.redis_client:
                await self.redis_client.close()
                self.is_connected = False
                logger.info("Redis connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")
            return False
    
    async def health_check(self) -> HealthStatus:
        """Check Redis health and performance metrics"""
        start_time = datetime.utcnow()
        
        try:
            # Ping Redis
            await self.redis_client.ping()
            
            # Get Redis info
            info = await self.redis_client.info()
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthStatus(
                is_healthy=True,
                response_time_ms=response_time,
                version=info.get('redis_version', 'unknown'),
                connection_count=info.get('connected_clients', 0),
                memory_usage_mb=info.get('used_memory', 0) / (1024 * 1024),
                disk_usage_mb=info.get('used_memory_rss', 0) / (1024 * 1024),
                additional_metrics={
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0),
                    'expired_keys': info.get('expired_keys', 0),
                    'evicted_keys': info.get('evicted_keys', 0),
                    'keys_count': await self._get_total_keys_count()
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
        """Set Redis keys/values"""
        start_time = datetime.utcnow()
        options = options or {}
        
        try:
            if isinstance(data, dict):
                # Single key-value operation
                if 'key' in data and 'value' in data:
                    key = f"{table_or_collection}:{data['key']}"
                    value = data['value']
                    
                    # Handle different value types
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    
                    # Set with optional TTL
                    ttl = options.get('ttl') or data.get('ttl')
                    if ttl:
                        await self.redis_client.setex(key, ttl, value)
                    else:
                        await self.redis_client.set(key, value)
                    
                    result_data = {'key': key, 'value': value, 'ttl': ttl}
                    affected_records = 1
                    
                elif 'hash_key' in data and 'hash_data' in data:
                    # Hash operation
                    hash_key = f"{table_or_collection}:{data['hash_key']}"
                    hash_data = data['hash_data']
                    
                    await self.redis_client.hset(hash_key, mapping=hash_data)
                    
                    # Set TTL if specified
                    ttl = options.get('ttl') or data.get('ttl')
                    if ttl:
                        await self.redis_client.expire(hash_key, ttl)
                    
                    result_data = {'hash_key': hash_key, 'hash_data': hash_data, 'ttl': ttl}
                    affected_records = len(hash_data)
                    
                else:
                    # Multiple key-value pairs in single dict
                    results = []
                    for key, value in data.items():
                        full_key = f"{table_or_collection}:{key}"
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        
                        ttl = options.get('ttl')
                        if ttl:
                            await self.redis_client.setex(full_key, ttl, value)
                        else:
                            await self.redis_client.set(full_key, value)
                        
                        results.append({'key': full_key, 'value': value, 'ttl': ttl})
                    
                    result_data = results
                    affected_records = len(results)
            
            else:
                # List of operations
                results = []
                for item in data:
                    if 'key' in item and 'value' in item:
                        key = f"{table_or_collection}:{item['key']}"
                        value = item['value']
                        
                        if isinstance(value, (dict, list)):
                            value = json.dumps(value)
                        
                        ttl = options.get('ttl') or item.get('ttl')
                        if ttl:
                            await self.redis_client.setex(key, ttl, value)
                        else:
                            await self.redis_client.set(key, value)
                        
                        results.append({'key': key, 'value': value, 'ttl': ttl})
                
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
                metadata={'operation_type': 'set', 'namespace': table_or_collection}
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
        """Get Redis keys/values"""
        start_time = datetime.utcnow()
        query = query or {}
        
        try:
            if 'key' in query:
                # Single key get
                key = f"{table_or_collection}:{query['key']}"
                value = await self.redis_client.get(key)
                
                if value:
                    # Try to parse JSON
                    try:
                        parsed_value = json.loads(value)
                    except:
                        parsed_value = value
                    
                    # Get TTL
                    ttl = await self.redis_client.ttl(key)
                    
                    result_data = {
                        'key': query['key'],
                        'value': parsed_value,
                        'ttl': ttl if ttl > 0 else None,
                        'full_key': key
                    }
                    count = 1
                else:
                    result_data = None
                    count = 0
            
            elif 'hash_key' in query:
                # Hash get
                hash_key = f"{table_or_collection}:{query['hash_key']}"
                
                if 'hash_field' in query:
                    # Get specific hash field
                    value = await self.redis_client.hget(hash_key, query['hash_field'])
                    result_data = {
                        'hash_key': query['hash_key'],
                        'hash_field': query['hash_field'],
                        'value': value,
                        'full_key': hash_key
                    }
                    count = 1 if value else 0
                else:
                    # Get all hash fields
                    hash_data = await self.redis_client.hgetall(hash_key)
                    ttl = await self.redis_client.ttl(hash_key)
                    
                    result_data = {
                        'hash_key': query['hash_key'],
                        'hash_data': hash_data,
                        'ttl': ttl if ttl > 0 else None,
                        'full_key': hash_key
                    }
                    count = len(hash_data)
            
            elif 'pattern' in query:
                # Pattern matching
                pattern = f"{table_or_collection}:{query['pattern']}"
                keys = await self.redis_client.keys(pattern)
                
                # Apply pagination
                if offset:
                    keys = keys[offset:]
                if limit:
                    keys = keys[:limit]
                
                # Get values for keys
                results = []
                if keys:
                    values = await self.redis_client.mget(keys)
                    
                    for key, value in zip(keys, values):
                        if value:
                            try:
                                parsed_value = json.loads(value)
                            except:
                                parsed_value = value
                            
                            # Remove namespace prefix
                            clean_key = key.replace(f"{table_or_collection}:", "")
                            ttl = await self.redis_client.ttl(key)
                            
                            results.append({
                                'key': clean_key,
                                'value': parsed_value,
                                'ttl': ttl if ttl > 0 else None,
                                'full_key': key
                            })
                
                result_data = results
                count = len(results)
            
            else:
                # Get all keys in namespace
                pattern = f"{table_or_collection}:*"
                keys = await self.redis_client.keys(pattern)
                
                # Apply pagination
                if offset:
                    keys = keys[offset:]
                if limit:
                    keys = keys[:limit]
                
                results = []
                if keys:
                    values = await self.redis_client.mget(keys)
                    
                    for key, value in zip(keys, values):
                        if value:
                            try:
                                parsed_value = json.loads(value)
                            except:
                                parsed_value = value
                            
                            clean_key = key.replace(f"{table_or_collection}:", "")
                            ttl = await self.redis_client.ttl(key)
                            
                            results.append({
                                'key': clean_key,
                                'value': parsed_value,
                                'ttl': ttl if ttl > 0 else None,
                                'full_key': key
                            })
                
                result_data = results
                count = len(results)
            
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
                    'operation_type': 'get',
                    'namespace': table_or_collection,
                    'query': query
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
        """Update Redis keys/values"""
        start_time = datetime.utcnow()
        options = options or {}
        
        try:
            if 'key' in query:
                # Update single key
                key = f"{table_or_collection}:{query['key']}"
                
                # Check if key exists
                exists = await self.redis_client.exists(key)
                if not exists and not options.get('upsert', False):
                    result_data = {'updated': False, 'reason': 'Key does not exist'}
                    affected_records = 0
                else:
                    value = update_data.get('value')
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    
                    # Update with optional TTL
                    ttl = options.get('ttl') or update_data.get('ttl')
                    if ttl:
                        await self.redis_client.setex(key, ttl, value)
                    else:
                        await self.redis_client.set(key, value)
                    
                    result_data = {'key': query['key'], 'value': value, 'ttl': ttl, 'updated': True}
                    affected_records = 1
            
            elif 'hash_key' in query:
                # Update hash fields
                hash_key = f"{table_or_collection}:{query['hash_key']}"
                hash_updates = update_data.get('hash_data', {})
                
                if hash_updates:
                    await self.redis_client.hset(hash_key, mapping=hash_updates)
                    
                    # Update TTL if specified
                    ttl = options.get('ttl') or update_data.get('ttl')
                    if ttl:
                        await self.redis_client.expire(hash_key, ttl)
                    
                    result_data = {
                        'hash_key': query['hash_key'],
                        'updated_fields': hash_updates,
                        'ttl': ttl,
                        'updated': True
                    }
                    affected_records = len(hash_updates)
                else:
                    result_data = {'updated': False, 'reason': 'No hash data provided'}
                    affected_records = 0
            
            elif 'pattern' in query:
                # Update multiple keys by pattern
                pattern = f"{table_or_collection}:{query['pattern']}"
                keys = await self.redis_client.keys(pattern)
                
                results = []
                for key in keys:
                    value = update_data.get('value')
                    if isinstance(value, (dict, list)):
                        value = json.dumps(value)
                    
                    ttl = options.get('ttl') or update_data.get('ttl')
                    if ttl:
                        await self.redis_client.setex(key, ttl, value)
                    else:
                        await self.redis_client.set(key, value)
                    
                    clean_key = key.replace(f"{table_or_collection}:", "")
                    results.append({'key': clean_key, 'value': value, 'ttl': ttl})
                
                result_data = results
                affected_records = len(results)
            
            else:
                result_data = {'updated': False, 'reason': 'No valid query criteria'}
                affected_records = 0
            
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
                    'operation_type': 'update',
                    'namespace': table_or_collection,
                    'query': query
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
        """Delete Redis keys"""
        start_time = datetime.utcnow()
        
        try:
            if 'key' in query:
                # Delete single key
                key = f"{table_or_collection}:{query['key']}"
                deleted_count = await self.redis_client.delete(key)
                
                result_data = {
                    'key': query['key'],
                    'deleted': deleted_count > 0,
                    'deleted_count': deleted_count
                }
                affected_records = deleted_count
            
            elif 'hash_key' in query and 'hash_field' in query:
                # Delete hash field
                hash_key = f"{table_or_collection}:{query['hash_key']}"
                deleted_count = await self.redis_client.hdel(hash_key, query['hash_field'])
                
                result_data = {
                    'hash_key': query['hash_key'],
                    'hash_field': query['hash_field'],
                    'deleted': deleted_count > 0,
                    'deleted_count': deleted_count
                }
                affected_records = deleted_count
            
            elif 'hash_key' in query:
                # Delete entire hash
                hash_key = f"{table_or_collection}:{query['hash_key']}"
                deleted_count = await self.redis_client.delete(hash_key)
                
                result_data = {
                    'hash_key': query['hash_key'],
                    'deleted': deleted_count > 0,
                    'deleted_count': deleted_count
                }
                affected_records = deleted_count
            
            elif 'pattern' in query:
                # Delete by pattern
                pattern = f"{table_or_collection}:{query['pattern']}"
                keys = await self.redis_client.keys(pattern)
                
                if keys:
                    deleted_count = await self.redis_client.delete(*keys)
                else:
                    deleted_count = 0
                
                result_data = {
                    'pattern': query['pattern'],
                    'keys_found': len(keys),
                    'deleted_count': deleted_count
                }
                affected_records = deleted_count
            
            else:
                # Delete all keys in namespace
                pattern = f"{table_or_collection}:*"
                keys = await self.redis_client.keys(pattern)
                
                if keys:
                    deleted_count = await self.redis_client.delete(*keys)
                else:
                    deleted_count = 0
                
                result_data = {
                    'namespace': table_or_collection,
                    'keys_found': len(keys),
                    'deleted_count': deleted_count
                }
                affected_records = deleted_count
            
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
                    'operation_type': 'delete',
                    'namespace': table_or_collection,
                    'query': query
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
        """Execute Redis commands"""
        start_time = datetime.utcnow()
        
        try:
            # Parse Redis command
            command_parts = query.split()
            command = command_parts[0].upper()
            args = command_parts[1:]
            
            if parameters:
                args.extend(parameters)
            
            # Execute Redis command
            if command == 'GET':
                result = await self.redis_client.get(args[0])
            elif command == 'SET':
                result = await self.redis_client.set(args[0], args[1])
            elif command == 'DEL':
                result = await self.redis_client.delete(*args)
            elif command == 'KEYS':
                result = await self.redis_client.keys(args[0])
            elif command == 'HGET':
                result = await self.redis_client.hget(args[0], args[1])
            elif command == 'HGETALL':
                result = await self.redis_client.hgetall(args[0])
            elif command == 'LPUSH':
                result = await self.redis_client.lpush(args[0], *args[1:])
            elif command == 'LRANGE':
                start_idx = int(args[1]) if len(args) > 1 else 0
                end_idx = int(args[2]) if len(args) > 2 else -1
                result = await self.redis_client.lrange(args[0], start_idx, end_idx)
            elif command == 'SADD':
                result = await self.redis_client.sadd(args[0], *args[1:])
            elif command == 'SMEMBERS':
                result = await self.redis_client.smembers(args[0])
            else:
                # Generic command execution
                result = await self.redis_client.execute_command(command, *args)
            
            operation = self.create_operation_metadata(
                OperationType.QUERY, 'redis_command', start_time, True,
                affected_records=1 if result else 0
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=True,
                data=result,
                count=1 if result else 0,
                execution_time_ms=operation.duration_ms,
                metadata={'operation_type': 'redis_command', 'command': command}
            )
            
        except Exception as e:
            error_msg = self.format_error_message('query', e)
            operation = self.create_operation_metadata(
                OperationType.QUERY, 'redis_command', start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def aggregate(self, table_or_collection: str, pipeline: List[Dict[str, Any]]) -> QueryResult:
        """Execute Redis aggregation operations"""
        start_time = datetime.utcnow()
        
        try:
            # Redis doesn't have built-in aggregation like MongoDB
            # This is a custom implementation for basic aggregations
            
            # Get all keys in namespace
            pattern = f"{table_or_collection}:*"
            keys = await self.redis_client.keys(pattern)
            
            # Get all values
            if not keys:
                result_data = []
            else:
                values = await self.redis_client.mget(keys)
                
                # Parse values and create documents
                documents = []
                for key, value in zip(keys, values):
                    if value:
                        try:
                            parsed_value = json.loads(value)
                        except:
                            parsed_value = {'value': value}
                        
                        # Add key information
                        clean_key = key.replace(f"{table_or_collection}:", "")
                        parsed_value['_key'] = clean_key
                        documents.append(parsed_value)
                
                # Apply pipeline stages
                result_data = documents
                for stage in pipeline:
                    if '$match' in stage:
                        # Filter documents
                        match_criteria = stage['$match']
                        filtered_docs = []
                        for doc in result_data:
                            if self._matches_criteria(doc, match_criteria):
                                filtered_docs.append(doc)
                        result_data = filtered_docs
                    
                    elif '$group' in stage:
                        # Group documents (basic implementation)
                        group_spec = stage['$group']
                        group_by = group_spec.get('_id')
                        
                        if group_by:
                            groups = {}
                            for doc in result_data:
                                group_key = doc.get(group_by, 'null')
                                if group_key not in groups:
                                    groups[group_key] = []
                                groups[group_key].append(doc)
                            
                            # Create group result
                            result_data = [
                                {'_id': group_key, 'count': len(docs), 'items': docs}
                                for group_key, docs in groups.items()
                            ]
                    
                    elif '$sort' in stage:
                        # Sort documents
                        sort_spec = stage['$sort']
                        for field, direction in sort_spec.items():
                            reverse = direction < 0
                            result_data.sort(
                                key=lambda x: x.get(field, ''),
                                reverse=reverse
                            )
                    
                    elif '$limit' in stage:
                        # Limit results
                        limit = stage['$limit']
                        result_data = result_data[:limit]
            
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
                    'namespace': table_or_collection,
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
        """Execute multiple Redis operations in pipeline"""
        results = []
        
        # Use Redis pipeline for better performance
        pipe = self.redis_client.pipeline()
        
        try:
            for op in operations:
                op_type = op.get('type')
                namespace = op.get('namespace', 'default')
                
                if op_type == 'create':
                    # Pipeline doesn't support our create method directly
                    # Execute individually for now
                    result = await self.create(namespace, op.get('data'), op.get('options'))
                    results.append(result)
                elif op_type == 'read':
                    result = await self.read(
                        namespace, op.get('query'), op.get('projection'),
                        op.get('limit'), op.get('offset'), op.get('sort')
                    )
                    results.append(result)
                elif op_type == 'update':
                    result = await self.update(
                        namespace, op.get('query'), op.get('update_data'), op.get('options')
                    )
                    results.append(result)
                elif op_type == 'delete':
                    result = await self.delete(namespace, op.get('query'), op.get('options'))
                    results.append(result)
                else:
                    results.append(QueryResult(
                        success=False,
                        data=None,
                        error_message=f"Unsupported operation type: {op_type}"
                    ))
        
        except Exception as e:
            # If pipeline fails, execute operations individually
            for op in operations:
                try:
                    op_type = op.get('type')
                    namespace = op.get('namespace', 'default')
                    
                    if op_type == 'create':
                        result = await self.create(namespace, op.get('data'), op.get('options'))
                    elif op_type == 'read':
                        result = await self.read(
                            namespace, op.get('query'), op.get('projection'),
                            op.get('limit'), op.get('offset'), op.get('sort')
                        )
                    elif op_type == 'update':
                        result = await self.update(
                            namespace, op.get('query'), op.get('update_data'), op.get('options')
                        )
                    elif op_type == 'delete':
                        result = await self.delete(namespace, op.get('query'), op.get('options'))
                    else:
                        result = QueryResult(
                            success=False,
                            data=None,
                            error_message=f"Unsupported operation type: {op_type}"
                        )
                    
                    results.append(result)
                except Exception as op_error:
                    results.append(QueryResult(
                        success=False,
                        data=None,
                        error_message=str(op_error)
                    ))
        
        return results
    
    # === Schema Management (Redis doesn't have schemas, but we can simulate) ===
    
    async def create_table_or_collection(self, name: str, schema: Dict[str, Any] = None) -> bool:
        """Create Redis namespace (conceptual)"""
        try:
            # Redis doesn't have collections, but we can create a metadata key
            metadata_key = f"_schema:{name}"
            schema_data = schema or {
                'created_at': datetime.utcnow().isoformat(),
                'namespace': name,
                'type': 'redis_namespace'
            }
            
            await self.redis_client.set(metadata_key, json.dumps(schema_data))
            logger.info(f"Redis namespace '{name}' created")
            return True
        except Exception as e:
            logger.error(f"Error creating Redis namespace '{name}': {e}")
            return False
    
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop Redis namespace (delete all keys with prefix)"""
        try:
            # Delete all keys with the namespace prefix
            pattern = f"{name}:*"
            keys = await self.redis_client.keys(pattern)
            
            if keys:
                await self.redis_client.delete(*keys)
            
            # Delete schema metadata
            metadata_key = f"_schema:{name}"
            await self.redis_client.delete(metadata_key)
            
            logger.info(f"Redis namespace '{name}' dropped")
            return True
        except Exception as e:
            logger.error(f"Error dropping Redis namespace '{name}': {e}")
            return False
    
    async def list_tables_or_collections(self) -> List[str]:
        """List Redis namespaces (from schema metadata)"""
        try:
            schema_keys = await self.redis_client.keys("_schema:*")
            namespaces = [key.replace("_schema:", "") for key in schema_keys]
            return namespaces
        except Exception as e:
            logger.error(f"Error listing Redis namespaces: {e}")
            return []
    
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get Redis namespace metadata"""
        try:
            metadata_key = f"_schema:{table_or_collection}"
            schema_data = await self.redis_client.get(metadata_key)
            
            if schema_data:
                schema = json.loads(schema_data)
            else:
                schema = {'namespace': table_or_collection, 'type': 'redis_namespace'}
            
            # Add current statistics
            pattern = f"{table_or_collection}:*"
            keys = await self.redis_client.keys(pattern)
            schema['key_count'] = len(keys)
            
            # Sample keys for analysis
            if keys:
                sample_keys = keys[:5]
                schema['sample_keys'] = [key.replace(f"{table_or_collection}:", "") for key in sample_keys]
            
            return schema
        except Exception as e:
            logger.error(f"Error getting schema for namespace '{table_or_collection}': {e}")
            return {}
    
    # === Index Management (Redis has limited indexing) ===
    
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Create Redis index (using sets for basic indexing)"""
        try:
            # Redis doesn't have traditional indexes, but we can create sets for indexing
            index_name = index_spec.get('name', f"idx_{table_or_collection}")
            fields = index_spec.get('fields', [])
            
            # Create index metadata
            index_key = f"_index:{table_or_collection}:{index_name}"
            index_metadata = {
                'name': index_name,
                'fields': fields,
                'namespace': table_or_collection,
                'created_at': datetime.utcnow().isoformat()
            }
            
            await self.redis_client.set(index_key, json.dumps(index_metadata))
            logger.info(f"Redis index '{index_name}' created for namespace '{table_or_collection}'")
            return True
        except Exception as e:
            logger.error(f"Error creating Redis index: {e}")
            return False
    
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Drop Redis index"""
        try:
            index_key = f"_index:{table_or_collection}:{index_name}"
            await self.redis_client.delete(index_key)
            logger.info(f"Redis index '{index_name}' dropped")
            return True
        except Exception as e:
            logger.error(f"Error dropping Redis index '{index_name}': {e}")
            return False
    
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """List Redis indexes for namespace"""
        try:
            pattern = f"_index:{table_or_collection}:*"
            index_keys = await self.redis_client.keys(pattern)
            
            indexes = []
            for index_key in index_keys:
                index_data = await self.redis_client.get(index_key)
                if index_data:
                    indexes.append(json.loads(index_data))
            
            return indexes
        except Exception as e:
            logger.error(f"Error listing Redis indexes: {e}")
            return []
    
    # === Transaction Support ===
    
    async def begin_transaction(self) -> Any:
        """Begin Redis transaction (MULTI)"""
        try:
            pipe = self.redis_client.pipeline()
            pipe.multi()
            return pipe
        except Exception as e:
            logger.error(f"Error starting Redis transaction: {e}")
            return None
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit Redis transaction (EXEC)"""
        try:
            await transaction.execute()
            return True
        except Exception as e:
            logger.error(f"Error committing Redis transaction: {e}")
            return False
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback Redis transaction (DISCARD)"""
        try:
            await transaction.discard()
            return True
        except Exception as e:
            logger.error(f"Error rolling back Redis transaction: {e}")
            return False
    
    # === Backup and Recovery ===
    
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Create Redis backup (using BGSAVE or data export)"""
        start_time = datetime.utcnow()
        backup_id = str(uuid.uuid4())
        
        try:
            # Trigger background save
            await self.redis_client.bgsave()
            
            # Get info about the backup
            info = await self.redis_client.info('persistence')
            
            # Get database size
            memory_info = await self.redis_client.info('memory')
            used_memory = memory_info.get('used_memory', 0)
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='snapshot',
                size_mb=used_memory / (1024 * 1024),
                location=backup_config.get('location', 'redis_dump.rdb'),
                timestamp=start_time,
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'backup_method': 'bgsave',
                    'rdb_last_save_time': info.get('rdb_last_save_time', 0)
                }
            )
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='snapshot',
                size_mb=0,
                location='',
                timestamp=start_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    async def restore_backup(self, backup_info: BackupInfo, 
                           restore_config: Dict[str, Any] = None) -> bool:
        """Restore Redis from backup"""
        try:
            # Redis restore typically requires server restart with RDB file
            logger.info(f"Redis restore for backup {backup_info.backup_id} requires manual intervention")
            return False
        except Exception as e:
            logger.error(f"Error restoring Redis backup: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """List available Redis backups"""
        # This would typically query backup storage
        return []
    
    # === Monitoring and Statistics ===
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        try:
            info = await self.redis_client.info()
            
            return {
                'redis_version': info.get('redis_version', 'unknown'),
                'used_memory_mb': info.get('used_memory', 0) / (1024 * 1024),
                'connected_clients': info.get('connected_clients', 0),
                'total_connections_received': info.get('total_connections_received', 0),
                'total_commands_processed': info.get('total_commands_processed', 0),
                'keyspace_hits': info.get('keyspace_hits', 0),
                'keyspace_misses': info.get('keyspace_misses', 0),
                'expired_keys': info.get('expired_keys', 0),
                'evicted_keys': info.get('evicted_keys', 0),
                'keys_count': await self._get_total_keys_count()
            }
        except Exception as e:
            logger.error(f"Error getting Redis statistics: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get Redis performance metrics"""
        try:
            info = await self.redis_client.info()
            
            return {
                'instantaneous_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'instantaneous_input_kbps': info.get('instantaneous_input_kbps', 0),
                'instantaneous_output_kbps': info.get('instantaneous_output_kbps', 0),
                'hit_rate': self._calculate_hit_rate(info),
                'memory_usage': {
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_rss': info.get('used_memory_rss', 0),
                    'used_memory_peak': info.get('used_memory_peak', 0),
                    'mem_fragmentation_ratio': info.get('mem_fragmentation_ratio', 0)
                }
            }
        except Exception as e:
            logger.error(f"Error getting Redis performance metrics: {e}")
            return {}
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get Redis slow log"""
        try:
            slow_log = await self.redis_client.slowlog_get(limit)
            
            return [
                {
                    'id': entry[0],
                    'timestamp': entry[1],
                    'duration_microseconds': entry[2],
                    'command': ' '.join(entry[3]),
                    'client_ip': entry[4] if len(entry) > 4 else 'unknown',
                    'client_name': entry[5] if len(entry) > 5 else 'unknown'
                }
                for entry in slow_log
            ]
        except Exception as e:
            logger.error(f"Error getting Redis slow log: {e}")
            return []
    
    # === Streaming Support ===
    
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream Redis data in batches"""
        try:
            pattern = f"{table_or_collection}:*"
            if query and 'pattern' in query:
                pattern = f"{table_or_collection}:{query['pattern']}"
            
            # Use SCAN for large datasets
            cursor = 0
            while True:
                cursor, keys = await self.redis_client.scan(cursor, match=pattern, count=batch_size)
                
                if keys:
                    # Get values for this batch
                    values = await self.redis_client.mget(keys)
                    
                    batch_data = []
                    for key, value in zip(keys, values):
                        if value:
                            try:
                                parsed_value = json.loads(value)
                            except:
                                parsed_value = value
                            
                            clean_key = key.replace(f"{table_or_collection}:", "")
                            ttl = await self.redis_client.ttl(key)
                            
                            batch_data.append({
                                'key': clean_key,
                                'value': parsed_value,
                                'ttl': ttl if ttl > 0 else None,
                                'full_key': key
                            })
                    
                    if batch_data:
                        yield batch_data
                
                if cursor == 0:
                    break
                    
        except Exception as e:
            logger.error(f"Error streaming Redis data: {e}")
            yield []
    
    # === Connection Pool Management ===
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get Redis connection pool statistics"""
        try:
            info = await self.redis_client.info('clients')
            
            return {
                'connected_clients': info.get('connected_clients', 0),
                'client_recent_max_input_buffer': info.get('client_recent_max_input_buffer', 0),
                'client_recent_max_output_buffer': info.get('client_recent_max_output_buffer', 0),
                'blocked_clients': info.get('blocked_clients', 0)
            }
        except Exception as e:
            logger.error(f"Error getting Redis pool stats: {e}")
            return {}
    
    async def reset_pool(self) -> bool:
        """Reset Redis connection"""
        try:
            await self.disconnect()
            return await self.connect()
        except Exception as e:
            logger.error(f"Error resetting Redis connection: {e}")
            return False
    
    # === Utility Methods ===
    
    async def _get_total_keys_count(self) -> int:
        """Get total number of keys in Redis"""
        try:
            info = await self.redis_client.info('keyspace')
            total_keys = 0
            
            for key, value in info.items():
                if key.startswith('db'):
                    # Parse something like "keys=1000,expires=0,avg_ttl=0"
                    key_info = dict(item.split('=') for item in value.split(','))
                    total_keys += int(key_info.get('keys', 0))
            
            return total_keys
        except:
            return 0
    
    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate Redis cache hit rate"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        
        if hits + misses == 0:
            return 100.0
        
        return (hits / (hits + misses)) * 100.0
    
    def _matches_criteria(self, document: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if document matches criteria (simplified)"""
        for field, value in criteria.items():
            if field not in document:
                return False
            
            if isinstance(value, dict):
                # Handle operators
                for op, op_value in value.items():
                    doc_value = document[field]
                    
                    if op == '$gt' and not (doc_value > op_value):
                        return False
                    elif op == '$gte' and not (doc_value >= op_value):
                        return False
                    elif op == '$lt' and not (doc_value < op_value):
                        return False
                    elif op == '$lte' and not (doc_value <= op_value):
                        return False
                    elif op == '$ne' and doc_value == op_value:
                        return False
                    elif op == '$in' and doc_value not in op_value:
                        return False
                    elif op == '$nin' and doc_value in op_value:
                        return False
            else:
                # Simple equality
                if document[field] != value:
                    return False
        
        return True
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get Redis-specific operations"""
        return [
            'pub_sub',
            'lua_script',
            'hyperloglog',
            'geo_operations',
            'stream_operations',
            'bitmap_operations',
            'sorted_set_operations'
        ]
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute Redis-specific operations"""
        parameters = parameters or {}
        
        if operation_name == 'pub_sub':
            channel = parameters.get('channel')
            message = parameters.get('message')
            action = parameters.get('action', 'publish')
            
            if action == 'publish':
                result = await self.redis_client.publish(channel, message)
                return {'published_to': channel, 'subscribers_reached': result}
            # Subscribe operations would need special handling
        
        elif operation_name == 'lua_script':
            script = parameters.get('script')
            keys = parameters.get('keys', [])
            args = parameters.get('args', [])
            
            result = await self.redis_client.eval(script, len(keys), *keys, *args)
            return result
        
        elif operation_name == 'hyperloglog':
            key = parameters.get('key')
            action = parameters.get('action')
            values = parameters.get('values', [])
            
            if action == 'add':
                return await self.redis_client.pfadd(key, *values)
            elif action == 'count':
                return await self.redis_client.pfcount(key)
        
        elif operation_name == 'sorted_set_operations':
            key = parameters.get('key')
            action = parameters.get('action')
            
            if action == 'add':
                members = parameters.get('members', {})  # {member: score}
                return await self.redis_client.zadd(key, members)
            elif action == 'range':
                start = parameters.get('start', 0)
                end = parameters.get('end', -1)
                return await self.redis_client.zrange(key, start, end, withscores=True)
        
        else:
            raise NotImplementedError(f"Redis operation '{operation_name}' not implemented")
