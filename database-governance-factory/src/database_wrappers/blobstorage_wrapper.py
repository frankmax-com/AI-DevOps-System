"""
Azure Blob Storage Wrapper
Comprehensive wrapper for Azure Blob Storage operations
"""

import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
import json
import uuid
import io
from urllib.parse import urlparse

try:
    from azure.storage.blob.aio import BlobServiceClient, ContainerClient, BlobClient
    from azure.storage.blob import BlobType, ContentSettings
    from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError
except ImportError:
    BlobServiceClient = None
    ContainerClient = None
    BlobClient = None
    BlobType = None
    ContentSettings = None
    ResourceNotFoundError = None
    ResourceExistsError = None

from .base_wrapper import (
    BaseDatabaseWrapper, DatabaseConfig, DatabaseOperation, QueryResult, 
    HealthStatus, BackupInfo, OperationType, DatabaseWrapperMixin
)

logger = logging.getLogger(__name__)

class BlobStorageWrapper(BaseDatabaseWrapper, DatabaseWrapperMixin):
    """
    Comprehensive Azure Blob Storage wrapper
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.blob_service_client = None
        self.default_container = config.database_name
        
    async def connect(self) -> bool:
        """Establish Blob Storage connection"""
        try:
            if not BlobServiceClient:
                raise ImportError("azure-storage-blob package is required for Blob Storage operations")
            
            # Create blob service client
            self.blob_service_client = BlobServiceClient.from_connection_string(
                self.config.connection_string,
                **self.config.additional_config
            )
            
            # Test connection by listing containers
            containers = []
            async for container in self.blob_service_client.list_containers(max_results=1):
                containers.append(container.name)
                break
            
            self.is_connected = True
            logger.info(f"Successfully connected to Azure Blob Storage")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Blob Storage: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close Blob Storage connection"""
        try:
            if self.blob_service_client:
                await self.blob_service_client.close()
                self.is_connected = False
                logger.info("Blob Storage connection closed")
            return True
        except Exception as e:
            logger.error(f"Error closing Blob Storage connection: {e}")
            return False
    
    async def health_check(self) -> HealthStatus:
        """Check Blob Storage health"""
        start_time = datetime.utcnow()
        
        try:
            # Get account information
            account_info = await self.blob_service_client.get_account_information()
            
            # Count containers
            container_count = 0
            async for container in self.blob_service_client.list_containers():
                container_count += 1
                if container_count >= 100:  # Limit to prevent timeout
                    break
            
            response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            return HealthStatus(
                is_healthy=True,
                response_time_ms=response_time,
                version='Azure Blob Storage',
                additional_metrics={
                    'account_kind': account_info.get('account_kind'),
                    'sku_name': account_info.get('sku_name'),
                    'container_count': container_count
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
        """Upload blobs to container"""
        start_time = datetime.utcnow()
        options = options or {}
        
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            # Ensure container exists
            try:
                await container_client.create_container()
            except ResourceExistsError:
                pass  # Container already exists
            
            if isinstance(data, dict):
                # Single blob upload
                blob_name = data.get('blob_name') or data.get('name') or str(uuid.uuid4())
                blob_data = data.get('data') or data.get('content', '')
                content_type = data.get('content_type', 'application/octet-stream')
                metadata = data.get('metadata', {})
                
                # Convert data to bytes if needed
                if isinstance(blob_data, str):
                    blob_data = blob_data.encode('utf-8')
                elif isinstance(blob_data, dict):
                    blob_data = json.dumps(blob_data).encode('utf-8')
                    content_type = 'application/json'
                
                # Upload blob
                blob_client = container_client.get_blob_client(blob_name)
                await blob_client.upload_blob(
                    blob_data,
                    overwrite=options.get('overwrite', False),
                    content_settings=ContentSettings(content_type=content_type),
                    metadata=metadata
                )
                
                result_data = {
                    'blob_name': blob_name,
                    'container': table_or_collection,
                    'size_bytes': len(blob_data),
                    'content_type': content_type,
                    'metadata': metadata
                }
                affected_records = 1
                
            else:
                # Multiple blob uploads
                results = []
                for item in data:
                    blob_name = item.get('blob_name') or item.get('name') or str(uuid.uuid4())
                    blob_data = item.get('data') or item.get('content', '')
                    content_type = item.get('content_type', 'application/octet-stream')
                    metadata = item.get('metadata', {})
                    
                    # Convert data to bytes if needed
                    if isinstance(blob_data, str):
                        blob_data = blob_data.encode('utf-8')
                    elif isinstance(blob_data, dict):
                        blob_data = json.dumps(blob_data).encode('utf-8')
                        content_type = 'application/json'
                    
                    # Upload blob
                    blob_client = container_client.get_blob_client(blob_name)
                    await blob_client.upload_blob(
                        blob_data,
                        overwrite=options.get('overwrite', False),
                        content_settings=ContentSettings(content_type=content_type),
                        metadata=metadata
                    )
                    
                    results.append({
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'size_bytes': len(blob_data),
                        'content_type': content_type,
                        'metadata': metadata
                    })
                
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
                metadata={'operation_type': 'upload_blob', 'container': table_or_collection}
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
        """Download blobs from container"""
        start_time = datetime.utcnow()
        query = query or {}
        
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            if 'blob_name' in query:
                # Download specific blob
                blob_name = query['blob_name']
                blob_client = container_client.get_blob_client(blob_name)
                
                try:
                    # Get blob properties
                    blob_properties = await blob_client.get_blob_properties()
                    
                    # Download blob content
                    include_content = query.get('include_content', True)
                    if include_content:
                        blob_data = await blob_client.download_blob()
                        content = await blob_data.readall()
                        
                        # Try to decode content
                        try:
                            if blob_properties.content_settings.content_type == 'application/json':
                                content = json.loads(content.decode('utf-8'))
                            else:
                                content = content.decode('utf-8')
                        except:
                            # Keep as bytes if decoding fails
                            pass
                    else:
                        content = None
                    
                    result_data = {
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'content': content,
                        'size_bytes': blob_properties.size,
                        'content_type': blob_properties.content_settings.content_type,
                        'last_modified': blob_properties.last_modified.isoformat() if blob_properties.last_modified else None,
                        'etag': blob_properties.etag,
                        'metadata': blob_properties.metadata
                    }
                    count = 1
                    
                except ResourceNotFoundError:
                    result_data = None
                    count = 0
            
            else:
                # List blobs in container
                prefix = query.get('prefix', '')
                name_starts_with = query.get('name_starts_with', prefix)
                
                blobs = []
                blob_count = 0
                
                async for blob in container_client.list_blobs(
                    name_starts_with=name_starts_with,
                    include=['metadata']
                ):
                    if offset and blob_count < offset:
                        blob_count += 1
                        continue
                    
                    if limit and len(blobs) >= limit:
                        break
                    
                    blob_info = {
                        'blob_name': blob.name,
                        'container': table_or_collection,
                        'size_bytes': blob.size,
                        'content_type': blob.content_settings.content_type if blob.content_settings else None,
                        'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                        'etag': blob.etag,
                        'metadata': blob.metadata or {}
                    }
                    
                    # Include content if requested and blob is small
                    if query.get('include_content', False) and blob.size < 1024 * 1024:  # 1MB limit
                        try:
                            blob_client = container_client.get_blob_client(blob.name)
                            blob_data = await blob_client.download_blob()
                            content = await blob_data.readall()
                            
                            try:
                                if blob.content_settings and blob.content_settings.content_type == 'application/json':
                                    content = json.loads(content.decode('utf-8'))
                                else:
                                    content = content.decode('utf-8')
                            except:
                                pass
                            
                            blob_info['content'] = content
                        except:
                            blob_info['content'] = None
                    
                    blobs.append(blob_info)
                    blob_count += 1
                
                result_data = blobs
                count = len(blobs)
            
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
                    'operation_type': 'download_blob',
                    'container': table_or_collection,
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
        """Update blob metadata or content"""
        start_time = datetime.utcnow()
        options = options or {}
        
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            if 'blob_name' in query:
                # Update specific blob
                blob_name = query['blob_name']
                blob_client = container_client.get_blob_client(blob_name)
                
                try:
                    updated_items = []
                    
                    # Update metadata
                    if 'metadata' in update_data:
                        await blob_client.set_blob_metadata(metadata=update_data['metadata'])
                        updated_items.append('metadata')
                    
                    # Update content
                    if 'content' in update_data or 'data' in update_data:
                        new_content = update_data.get('content') or update_data.get('data')
                        content_type = update_data.get('content_type', 'application/octet-stream')
                        
                        # Convert data to bytes if needed
                        if isinstance(new_content, str):
                            new_content = new_content.encode('utf-8')
                        elif isinstance(new_content, dict):
                            new_content = json.dumps(new_content).encode('utf-8')
                            content_type = 'application/json'
                        
                        await blob_client.upload_blob(
                            new_content,
                            overwrite=True,
                            content_settings=ContentSettings(content_type=content_type)
                        )
                        updated_items.append('content')
                    
                    # Update properties
                    if 'content_type' in update_data:
                        content_settings = ContentSettings(content_type=update_data['content_type'])
                        await blob_client.set_http_headers(content_settings=content_settings)
                        updated_items.append('content_type')
                    
                    result_data = {
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'updated_items': updated_items,
                        'success': True
                    }
                    affected_records = 1
                    
                except ResourceNotFoundError:
                    result_data = {
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'success': False,
                        'error': 'Blob not found'
                    }
                    affected_records = 0
            
            else:
                # Update multiple blobs by pattern
                prefix = query.get('prefix', '')
                updated_blobs = []
                
                async for blob in container_client.list_blobs(name_starts_with=prefix):
                    blob_client = container_client.get_blob_client(blob.name)
                    
                    try:
                        updated_items = []
                        
                        # Update metadata
                        if 'metadata' in update_data:
                            await blob_client.set_blob_metadata(metadata=update_data['metadata'])
                            updated_items.append('metadata')
                        
                        # Update properties
                        if 'content_type' in update_data:
                            content_settings = ContentSettings(content_type=update_data['content_type'])
                            await blob_client.set_http_headers(content_settings=content_settings)
                            updated_items.append('content_type')
                        
                        updated_blobs.append({
                            'blob_name': blob.name,
                            'updated_items': updated_items,
                            'success': True
                        })
                        
                    except Exception as blob_error:
                        updated_blobs.append({
                            'blob_name': blob.name,
                            'success': False,
                            'error': str(blob_error)
                        })
                
                result_data = updated_blobs
                affected_records = len([blob for blob in updated_blobs if blob['success']])
            
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
                    'operation_type': 'update_blob',
                    'container': table_or_collection,
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
        """Delete blobs from container"""
        start_time = datetime.utcnow()
        
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            if 'blob_name' in query:
                # Delete specific blob
                blob_name = query['blob_name']
                blob_client = container_client.get_blob_client(blob_name)
                
                try:
                    await blob_client.delete_blob()
                    result_data = {
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'deleted': True
                    }
                    affected_records = 1
                    
                except ResourceNotFoundError:
                    result_data = {
                        'blob_name': blob_name,
                        'container': table_or_collection,
                        'deleted': False,
                        'reason': 'Blob not found'
                    }
                    affected_records = 0
            
            elif 'prefix' in query:
                # Delete blobs by prefix
                prefix = query['prefix']
                deleted_blobs = []
                
                async for blob in container_client.list_blobs(name_starts_with=prefix):
                    blob_client = container_client.get_blob_client(blob.name)
                    
                    try:
                        await blob_client.delete_blob()
                        deleted_blobs.append({
                            'blob_name': blob.name,
                            'deleted': True
                        })
                    except Exception as delete_error:
                        deleted_blobs.append({
                            'blob_name': blob.name,
                            'deleted': False,
                            'error': str(delete_error)
                        })
                
                result_data = deleted_blobs
                affected_records = len([blob for blob in deleted_blobs if blob['deleted']])
            
            else:
                # Delete entire container
                try:
                    await container_client.delete_container()
                    result_data = {
                        'container': table_or_collection,
                        'deleted': True,
                        'operation': 'delete_container'
                    }
                    affected_records = 1
                    
                except ResourceNotFoundError:
                    result_data = {
                        'container': table_or_collection,
                        'deleted': False,
                        'reason': 'Container not found'
                    }
                    affected_records = 0
            
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
                    'operation_type': 'delete_blob',
                    'container': table_or_collection,
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
        """Execute blob storage operations via query string"""
        start_time = datetime.utcnow()
        
        try:
            # Parse query operations for blob storage
            # Format: "OPERATION container_name [parameters]"
            parts = query.split()
            operation = parts[0].upper()
            container_name = parts[1] if len(parts) > 1 else self.default_container
            
            if operation == 'LIST':
                # List blobs
                result = await self.read(container_name, {'include_content': False})
                return result
            
            elif operation == 'CONTAINERS':
                # List containers
                containers = []
                async for container in self.blob_service_client.list_containers():
                    containers.append({
                        'name': container.name,
                        'last_modified': container.last_modified.isoformat() if container.last_modified else None,
                        'metadata': container.metadata or {}
                    })
                
                operation_meta = self.create_operation_metadata(
                    OperationType.QUERY, 'containers', start_time, True,
                    affected_records=len(containers)
                )
                self.log_operation(operation_meta)
                
                return QueryResult(
                    success=True,
                    data=containers,
                    count=len(containers),
                    execution_time_ms=operation_meta.duration_ms,
                    metadata={'operation_type': 'list_containers'}
                )
            
            else:
                raise ValueError(f"Unsupported blob storage operation: {operation}")
                
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
        """Aggregate blob storage data"""
        start_time = datetime.utcnow()
        
        try:
            # Get all blobs in container
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            blobs = []
            async for blob in container_client.list_blobs(include=['metadata']):
                blob_data = {
                    'name': blob.name,
                    'size': blob.size,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                    'last_modified': blob.last_modified,
                    'metadata': blob.metadata or {}
                }
                blobs.append(blob_data)
            
            # Apply pipeline stages
            result_data = blobs
            for stage in pipeline:
                if '$match' in stage:
                    # Filter blobs
                    match_criteria = stage['$match']
                    filtered_blobs = []
                    for blob in result_data:
                        if self._matches_blob_criteria(blob, match_criteria):
                            filtered_blobs.append(blob)
                    result_data = filtered_blobs
                
                elif '$group' in stage:
                    # Group blobs
                    group_spec = stage['$group']
                    group_by = group_spec.get('_id')
                    
                    if group_by == 'content_type':
                        groups = {}
                        for blob in result_data:
                            content_type = blob.get('content_type', 'unknown')
                            if content_type not in groups:
                                groups[content_type] = {'count': 0, 'total_size': 0, 'blobs': []}
                            groups[content_type]['count'] += 1
                            groups[content_type]['total_size'] += blob.get('size', 0)
                            groups[content_type]['blobs'].append(blob['name'])
                        
                        result_data = [
                            {'_id': content_type, **stats}
                            for content_type, stats in groups.items()
                        ]
                
                elif '$sort' in stage:
                    # Sort blobs
                    sort_spec = stage['$sort']
                    for field, direction in sort_spec.items():
                        reverse = direction < 0
                        result_data.sort(
                            key=lambda x: x.get(field, 0),
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
                    'container': table_or_collection,
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
        """Execute multiple blob operations"""
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
        """Create blob container"""
        try:
            container_client = self.blob_service_client.get_container_client(name)
            
            metadata = schema.get('metadata', {}) if schema else {}
            public_access = schema.get('public_access') if schema else None
            
            await container_client.create_container(
                metadata=metadata,
                public_access=public_access
            )
            
            logger.info(f"Blob container '{name}' created successfully")
            return True
            
        except ResourceExistsError:
            logger.info(f"Blob container '{name}' already exists")
            return True
        except Exception as e:
            logger.error(f"Error creating blob container '{name}': {e}")
            return False
    
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop blob container"""
        try:
            container_client = self.blob_service_client.get_container_client(name)
            await container_client.delete_container()
            logger.info(f"Blob container '{name}' dropped successfully")
            return True
        except Exception as e:
            logger.error(f"Error dropping blob container '{name}': {e}")
            return False
    
    async def list_tables_or_collections(self) -> List[str]:
        """List all blob containers"""
        try:
            containers = []
            async for container in self.blob_service_client.list_containers():
                containers.append(container.name)
            return containers
        except Exception as e:
            logger.error(f"Error listing blob containers: {e}")
            return []
    
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get blob container information"""
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            properties = await container_client.get_container_properties()
            
            # Count blobs
            blob_count = 0
            total_size = 0
            content_types = {}
            
            async for blob in container_client.list_blobs():
                blob_count += 1
                total_size += blob.size or 0
                
                content_type = blob.content_settings.content_type if blob.content_settings else 'unknown'
                content_types[content_type] = content_types.get(content_type, 0) + 1
            
            return {
                'container_name': table_or_collection,
                'last_modified': properties.last_modified.isoformat() if properties.last_modified else None,
                'etag': properties.etag,
                'metadata': properties.metadata or {},
                'public_access': properties.public_access,
                'blob_count': blob_count,
                'total_size_bytes': total_size,
                'content_types': content_types
            }
        except Exception as e:
            logger.error(f"Error getting schema for container '{table_or_collection}': {e}")
            return {}
    
    # === Index Management (Not applicable to blob storage) ===
    
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Blob storage doesn't support indexes"""
        logger.warning("Blob storage doesn't support traditional indexes")
        return False
    
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Blob storage doesn't support indexes"""
        return False
    
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """Blob storage doesn't support indexes"""
        return []
    
    # === Transaction Support ===
    
    async def begin_transaction(self) -> Any:
        """Blob storage doesn't support transactions"""
        logger.warning("Blob storage doesn't support transactions")
        return None
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Blob storage doesn't support transactions"""
        return False
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Blob storage doesn't support transactions"""
        return False
    
    # === Backup and Recovery ===
    
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Create blob storage backup (copy to another container)"""
        start_time = datetime.utcnow()
        backup_id = str(uuid.uuid4())
        
        try:
            source_container = backup_config.get('source_container', self.default_container)
            backup_container = backup_config.get('backup_container', f"backup-{backup_id}")
            
            # Create backup container
            backup_container_client = self.blob_service_client.get_container_client(backup_container)
            await backup_container_client.create_container()
            
            # Copy blobs
            source_container_client = self.blob_service_client.get_container_client(source_container)
            
            copied_count = 0
            total_size = 0
            
            async for blob in source_container_client.list_blobs():
                source_blob_client = source_container_client.get_blob_client(blob.name)
                backup_blob_client = backup_container_client.get_blob_client(blob.name)
                
                # Copy blob
                await backup_blob_client.start_copy_from_url(source_blob_client.url)
                
                copied_count += 1
                total_size += blob.size or 0
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='container_copy',
                size_mb=total_size / (1024 * 1024),
                location=backup_container,
                timestamp=start_time,
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'source_container': source_container,
                    'backup_container': backup_container,
                    'blobs_copied': copied_count
                }
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='container_copy',
                size_mb=0,
                location='',
                timestamp=start_time,
                duration_ms=duration_ms,
                success=False,
                error_message=str(e)
            )
    
    async def restore_backup(self, backup_info: BackupInfo, 
                           restore_config: Dict[str, Any] = None) -> bool:
        """Restore from backup container"""
        try:
            restore_config = restore_config or {}
            backup_container = backup_info.location
            target_container = restore_config.get('target_container', self.default_container)
            
            backup_container_client = self.blob_service_client.get_container_client(backup_container)
            target_container_client = self.blob_service_client.get_container_client(target_container)
            
            # Create target container if it doesn't exist
            try:
                await target_container_client.create_container()
            except ResourceExistsError:
                pass
            
            # Copy blobs from backup to target
            async for blob in backup_container_client.list_blobs():
                source_blob_client = backup_container_client.get_blob_client(blob.name)
                target_blob_client = target_container_client.get_blob_client(blob.name)
                
                await target_blob_client.start_copy_from_url(source_blob_client.url)
            
            return True
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """List backup containers"""
        try:
            backups = []
            async for container in self.blob_service_client.list_containers():
                if container.name.startswith('backup-'):
                    # This is a basic implementation
                    backups.append(BackupInfo(
                        backup_id=container.name.replace('backup-', ''),
                        backup_type='container_copy',
                        size_mb=0,  # Would need to calculate
                        location=container.name,
                        timestamp=container.last_modified or datetime.utcnow(),
                        duration_ms=0,
                        success=True
                    ))
            return backups
        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []
    
    # === Monitoring and Statistics ===
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get blob storage statistics"""
        try:
            account_info = await self.blob_service_client.get_account_information()
            
            # Count containers and blobs
            container_count = 0
            total_blobs = 0
            total_size = 0
            
            async for container in self.blob_service_client.list_containers():
                container_count += 1
                container_client = self.blob_service_client.get_container_client(container.name)
                
                async for blob in container_client.list_blobs():
                    total_blobs += 1
                    total_size += blob.size or 0
            
            return {
                'account_kind': account_info.account_kind,
                'sku_name': account_info.sku_name,
                'container_count': container_count,
                'total_blobs': total_blobs,
                'total_size_bytes': total_size,
                'total_size_mb': total_size / (1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Error getting blob storage statistics: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get blob storage performance metrics"""
        try:
            return {
                'note': 'Performance metrics available through Azure Monitor',
                'throughput': 'Depends on storage account type and tier',
                'latency': 'Varies by region and access pattern'
            }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Blob storage doesn't have slow queries"""
        return []
    
    # === Streaming Support ===
    
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream blob metadata in batches"""
        try:
            container_client = self.blob_service_client.get_container_client(table_or_collection)
            
            prefix = query.get('prefix', '') if query else ''
            
            batch = []
            async for blob in container_client.list_blobs(
                name_starts_with=prefix,
                include=['metadata']
            ):
                blob_info = {
                    'blob_name': blob.name,
                    'container': table_or_collection,
                    'size_bytes': blob.size,
                    'content_type': blob.content_settings.content_type if blob.content_settings else None,
                    'last_modified': blob.last_modified.isoformat() if blob.last_modified else None,
                    'etag': blob.etag,
                    'metadata': blob.metadata or {}
                }
                
                batch.append(blob_info)
                
                if len(batch) >= batch_size:
                    yield batch
                    batch = []
            
            # Yield remaining items
            if batch:
                yield batch
                
        except Exception as e:
            logger.error(f"Error streaming blob data: {e}")
            yield []
    
    # === Connection Pool Management ===
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Blob storage connection stats"""
        return {
            'connection_type': 'HTTP/HTTPS',
            'note': 'Blob storage uses REST API connections'
        }
    
    async def reset_pool(self) -> bool:
        """Reset blob storage connection"""
        try:
            await self.disconnect()
            return await self.connect()
        except Exception as e:
            logger.error(f"Error resetting blob storage connection: {e}")
            return False
    
    # === Utility Methods ===
    
    def _matches_blob_criteria(self, blob: Dict[str, Any], criteria: Dict[str, Any]) -> bool:
        """Check if blob matches criteria"""
        for field, value in criteria.items():
            if field not in blob:
                return False
            
            if isinstance(value, dict):
                # Handle operators
                for op, op_value in value.items():
                    blob_value = blob[field]
                    
                    if op == '$gt' and not (blob_value > op_value):
                        return False
                    elif op == '$gte' and not (blob_value >= op_value):
                        return False
                    elif op == '$lt' and not (blob_value < op_value):
                        return False
                    elif op == '$lte' and not (blob_value <= op_value):
                        return False
                    elif op == '$ne' and blob_value == op_value:
                        return False
                    elif op == '$in' and blob_value not in op_value:
                        return False
                    elif op == '$regex' and not re.search(op_value, str(blob_value)):
                        return False
            else:
                # Simple equality
                if blob[field] != value:
                    return False
        
        return True
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get blob storage-specific operations"""
        return [
            'generate_sas_token',
            'set_blob_tier',
            'create_snapshot',
            'lease_blob',
            'copy_blob'
        ]
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute blob storage-specific operations"""
        parameters = parameters or {}
        
        if operation_name == 'generate_sas_token':
            # This would require implementing SAS token generation
            logger.warning("SAS token generation requires additional Azure SDK setup")
            return {'note': 'SAS token generation not implemented in this wrapper'}
        
        elif operation_name == 'set_blob_tier':
            container_name = parameters.get('container')
            blob_name = parameters.get('blob_name')
            tier = parameters.get('tier', 'Hot')
            
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            await blob_client.set_standard_blob_tier(tier)
            return {'blob_name': blob_name, 'tier': tier, 'success': True}
        
        elif operation_name == 'create_snapshot':
            container_name = parameters.get('container')
            blob_name = parameters.get('blob_name')
            
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)
            
            snapshot = await blob_client.create_snapshot()
            return {'blob_name': blob_name, 'snapshot': snapshot['snapshot'], 'success': True}
        
        else:
            raise NotImplementedError(f"Blob storage operation '{operation_name}' not implemented")
