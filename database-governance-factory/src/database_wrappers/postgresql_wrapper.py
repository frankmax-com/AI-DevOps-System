"""
PostgreSQL Database Wrapper
Comprehensive wrapper for PostgreSQL operations with full SQL support
"""

import logging
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from datetime import datetime
import asyncio
import asyncpg
import json
import uuid
from urllib.parse import urlparse

from .base_wrapper import (
    BaseDatabaseWrapper, DatabaseConfig, DatabaseOperation, QueryResult, 
    HealthStatus, BackupInfo, OperationType, DatabaseWrapperMixin
)

logger = logging.getLogger(__name__)

class PostgreSQLWrapper(BaseDatabaseWrapper, DatabaseWrapperMixin):
    """
    Comprehensive PostgreSQL wrapper with full SQL support
    """
    
    def __init__(self, config: DatabaseConfig):
        super().__init__(config)
        self.connection_pool: Optional[asyncpg.Pool] = None
        self.current_connection: Optional[asyncpg.Connection] = None
        
    async def connect(self) -> bool:
        """Establish PostgreSQL connection pool"""
        try:
            # Parse connection string or use direct parameters
            connection_kwargs = {
                'min_size': 1,
                'max_size': self.config.pool_size,
                'command_timeout': self.config.timeout,
                **self.config.additional_config
            }
            
            if self.config.ssl_enabled:
                connection_kwargs['ssl'] = 'require'
            
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                self.config.connection_string,
                **connection_kwargs
            )
            
            # Test connection
            async with self.connection_pool.acquire() as conn:
                await conn.execute('SELECT 1')
            
            self.is_connected = True
            logger.info(f"Successfully connected to PostgreSQL: {self.config.database_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> bool:
        """Close PostgreSQL connection pool"""
        try:
            if self.connection_pool:
                await self.connection_pool.close()
                self.is_connected = False
                logger.info("PostgreSQL connection pool closed")
            return True
        except Exception as e:
            logger.error(f"Error closing PostgreSQL connection: {e}")
            return False
    
    async def health_check(self) -> HealthStatus:
        """Check PostgreSQL health and performance metrics"""
        start_time = datetime.utcnow()
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Basic health check
                await conn.execute('SELECT 1')
                
                # Get version
                version_result = await conn.fetchrow('SELECT version()')
                version = version_result['version'].split()[1] if version_result else 'unknown'
                
                # Get connection count
                conn_count_result = await conn.fetchrow(
                    'SELECT count(*) as active_connections FROM pg_stat_activity'
                )
                connection_count = conn_count_result['active_connections'] if conn_count_result else 0
                
                # Get database size
                db_size_result = await conn.fetchrow(
                    'SELECT pg_size_pretty(pg_database_size($1)) as size, '
                    'pg_database_size($1) as size_bytes',
                    self.config.database_name
                )
                
                disk_usage_mb = 0
                if db_size_result and db_size_result['size_bytes']:
                    disk_usage_mb = db_size_result['size_bytes'] / (1024 * 1024)
                
                # Get memory usage (shared_buffers setting)
                memory_result = await conn.fetchrow('SHOW shared_buffers')
                memory_setting = memory_result['shared_buffers'] if memory_result else '128MB'
                
                response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                
                return HealthStatus(
                    is_healthy=True,
                    response_time_ms=response_time,
                    version=version,
                    connection_count=connection_count,
                    memory_usage_mb=self._parse_memory_setting(memory_setting),
                    disk_usage_mb=disk_usage_mb,
                    additional_metrics={
                        'database_size': db_size_result['size'] if db_size_result else 'unknown',
                        'shared_buffers': memory_setting
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
        """Insert records into PostgreSQL table"""
        start_time = datetime.utcnow()
        
        try:
            async with self.connection_pool.acquire() as conn:
                if isinstance(data, dict):
                    # Single record insert
                    columns = list(data.keys())
                    values = list(data.values())
                    placeholders = ', '.join([f'${i+1}' for i in range(len(values))])
                    
                    query = f"""
                    INSERT INTO {table_or_collection} ({', '.join(columns)})
                    VALUES ({placeholders})
                    RETURNING *
                    """
                    
                    result = await conn.fetchrow(query, *values)
                    inserted_data = dict(result) if result else data
                    affected_records = 1
                    
                else:
                    # Multiple records insert
                    if not data:
                        raise ValueError("No data provided for insert")
                    
                    columns = list(data[0].keys())
                    
                    # Build VALUES clause for multiple records
                    values_list = []
                    all_values = []
                    
                    for i, record in enumerate(data):
                        record_values = [record.get(col) for col in columns]
                        placeholders = ', '.join([f'${len(all_values) + j + 1}' for j in range(len(record_values))])
                        values_list.append(f'({placeholders})')
                        all_values.extend(record_values)
                    
                    query = f"""
                    INSERT INTO {table_or_collection} ({', '.join(columns)})
                    VALUES {', '.join(values_list)}
                    RETURNING *
                    """
                    
                    results = await conn.fetch(query, *all_values)
                    inserted_data = [dict(row) for row in results]
                    affected_records = len(results)
                
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
                    metadata={'operation_type': 'insert', 'table': table_or_collection}
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
        """Read records from PostgreSQL table"""
        start_time = datetime.utcnow()
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Build SELECT clause
                if projection:
                    if isinstance(projection, dict):
                        # Handle MongoDB-style projection {field: 1, field2: 0}
                        included_fields = [k for k, v in projection.items() if v == 1]
                        excluded_fields = [k for k, v in projection.items() if v == 0]
                        
                        if included_fields:
                            select_clause = ', '.join(included_fields)
                        else:
                            # Get all columns and exclude specified ones
                            columns_result = await conn.fetch(
                                "SELECT column_name FROM information_schema.columns WHERE table_name = $1",
                                table_or_collection
                            )
                            all_columns = [row['column_name'] for row in columns_result]
                            select_columns = [col for col in all_columns if col not in excluded_fields]
                            select_clause = ', '.join(select_columns) if select_columns else '*'
                    else:
                        select_clause = ', '.join(projection) if isinstance(projection, list) else str(projection)
                else:
                    select_clause = '*'
                
                # Build WHERE clause
                where_clause = ''
                where_values = []
                if query:
                    where_conditions, where_values = self._build_where_clause(query)
                    where_clause = f'WHERE {where_conditions}' if where_conditions else ''
                
                # Build ORDER BY clause
                order_clause = ''
                if sort:
                    order_parts = []
                    for field, direction in sort.items():
                        order_dir = 'ASC' if direction > 0 else 'DESC'
                        order_parts.append(f'{field} {order_dir}')
                    order_clause = f'ORDER BY {", ".join(order_parts)}'
                
                # Build LIMIT and OFFSET clauses
                limit_clause = f'LIMIT {limit}' if limit else ''
                offset_clause = f'OFFSET {offset}' if offset else ''
                
                # Construct final query
                sql_query = f"""
                SELECT {select_clause} 
                FROM {table_or_collection} 
                {where_clause} 
                {order_clause} 
                {limit_clause} 
                {offset_clause}
                """.strip()
                
                # Execute query
                results = await conn.fetch(sql_query, *where_values)
                data = [dict(row) for row in results]
                
                # Get total count for pagination
                if limit is not None:
                    count_query = f'SELECT COUNT(*) as total FROM {table_or_collection} {where_clause}'
                    count_result = await conn.fetchrow(count_query, *where_values)
                    total_count = count_result['total'] if count_result else 0
                else:
                    total_count = len(data)
                
                # Log operation
                operation = self.create_operation_metadata(
                    OperationType.READ, table_or_collection, start_time, True,
                    affected_records=len(data)
                )
                self.log_operation(operation)
                
                return QueryResult(
                    success=True,
                    data=data,
                    count=total_count,
                    execution_time_ms=operation.duration_ms,
                    metadata={
                        'operation_type': 'select',
                        'table': table_or_collection,
                        'query': str(query),
                        'projection': projection,
                        'limit': limit,
                        'offset': offset,
                        'sql': sql_query
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
        """Update records in PostgreSQL table"""
        start_time = datetime.utcnow()
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Build SET clause
                set_parts = []
                set_values = []
                param_index = 1
                
                for field, value in update_data.items():
                    set_parts.append(f'{field} = ${param_index}')
                    set_values.append(value)
                    param_index += 1
                
                set_clause = ', '.join(set_parts)
                
                # Build WHERE clause
                where_conditions, where_values = self._build_where_clause(query, param_index)
                where_clause = f'WHERE {where_conditions}' if where_conditions else ''
                
                # Combine all values
                all_values = set_values + where_values
                
                # Construct UPDATE query
                sql_query = f"""
                UPDATE {table_or_collection} 
                SET {set_clause} 
                {where_clause} 
                RETURNING *
                """
                
                # Execute update
                results = await conn.fetch(sql_query, *all_values)
                updated_data = [dict(row) for row in results]
                affected_records = len(results)
                
                # Log operation
                operation = self.create_operation_metadata(
                    OperationType.UPDATE, table_or_collection, start_time, True,
                    affected_records=affected_records
                )
                self.log_operation(operation)
                
                return QueryResult(
                    success=True,
                    data=updated_data,
                    count=affected_records,
                    execution_time_ms=operation.duration_ms,
                    metadata={
                        'operation_type': 'update',
                        'table': table_or_collection,
                        'query': str(query),
                        'update_data': update_data,
                        'sql': sql_query
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
        """Delete records from PostgreSQL table"""
        start_time = datetime.utcnow()
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Build WHERE clause
                where_conditions, where_values = self._build_where_clause(query)
                where_clause = f'WHERE {where_conditions}' if where_conditions else ''
                
                # Construct DELETE query
                sql_query = f'DELETE FROM {table_or_collection} {where_clause} RETURNING *'
                
                # Execute delete
                results = await conn.fetch(sql_query, *where_values)
                deleted_data = [dict(row) for row in results]
                affected_records = len(results)
                
                # Log operation
                operation = self.create_operation_metadata(
                    OperationType.DELETE, table_or_collection, start_time, True,
                    affected_records=affected_records
                )
                self.log_operation(operation)
                
                return QueryResult(
                    success=True,
                    data=deleted_data,
                    count=affected_records,
                    execution_time_ms=operation.duration_ms,
                    metadata={
                        'operation_type': 'delete',
                        'table': table_or_collection,
                        'query': str(query),
                        'sql': sql_query
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
        """Execute raw SQL query"""
        start_time = datetime.utcnow()
        parameters = parameters or []
        
        try:
            async with self.connection_pool.acquire() as conn:
                # Determine if it's a SELECT query or other
                query_type = query.strip().upper().split()[0]
                
                if query_type == 'SELECT':
                    results = await conn.fetch(query, *parameters)
                    data = [dict(row) for row in results]
                    affected_records = len(data)
                else:
                    # For INSERT, UPDATE, DELETE, etc.
                    result = await conn.execute(query, *parameters)
                    # Parse affected rows from result string
                    affected_records = self._parse_affected_rows(result)
                    data = {'result': result, 'affected_rows': affected_records}
                
                operation = self.create_operation_metadata(
                    OperationType.QUERY, 'custom_query', start_time, True,
                    affected_records=affected_records
                )
                self.log_operation(operation)
                
                return QueryResult(
                    success=True,
                    data=data,
                    count=affected_records,
                    execution_time_ms=operation.duration_ms,
                    metadata={'operation_type': query_type.lower(), 'sql': query}
                )
                
        except Exception as e:
            error_msg = self.format_error_message('query', e)
            operation = self.create_operation_metadata(
                OperationType.QUERY, 'custom_query', start_time, False, error_msg
            )
            self.log_operation(operation)
            
            return QueryResult(
                success=False,
                data=None,
                error_message=error_msg,
                execution_time_ms=operation.duration_ms
            )
    
    async def aggregate(self, table_or_collection: str, pipeline: List[Dict[str, Any]]) -> QueryResult:
        """Execute SQL aggregation query"""
        start_time = datetime.utcnow()
        
        try:
            # Convert pipeline to SQL aggregation
            # This is a simplified implementation - real implementation would be more complex
            sql_query = self._convert_pipeline_to_sql(table_or_collection, pipeline)
            
            async with self.connection_pool.acquire() as conn:
                results = await conn.fetch(sql_query)
                data = [dict(row) for row in results]
                
                operation = self.create_operation_metadata(
                    OperationType.AGGREGATE, table_or_collection, start_time, True,
                    affected_records=len(data)
                )
                self.log_operation(operation)
                
                return QueryResult(
                    success=True,
                    data=data,
                    count=len(data),
                    execution_time_ms=operation.duration_ms,
                    metadata={
                        'operation_type': 'aggregate',
                        'table': table_or_collection,
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
        """Execute multiple operations in batch"""
        results = []
        
        async with self.connection_pool.acquire() as conn:
            async with conn.transaction():
                for op in operations:
                    op_type = op.get('type')
                    table_name = op.get('table')
                    
                    if op_type == 'create':
                        result = await self.create(table_name, op.get('data'), op.get('options'))
                    elif op_type == 'read':
                        result = await self.read(
                            table_name, op.get('query'), op.get('projection'),
                            op.get('limit'), op.get('offset'), op.get('sort')
                        )
                    elif op_type == 'update':
                        result = await self.update(
                            table_name, op.get('query'), op.get('update_data'), op.get('options')
                        )
                    elif op_type == 'delete':
                        result = await self.delete(table_name, op.get('query'), op.get('options'))
                    elif op_type == 'query':
                        result = await self.query(op.get('sql'), op.get('parameters'))
                    else:
                        result = QueryResult(
                            success=False,
                            data=None,
                            error_message=f"Unsupported operation type: {op_type}"
                        )
                    
                    results.append(result)
                    
                    # If any operation fails, rollback transaction
                    if not result.success:
                        break
        
        return results
    
    # === Schema Management ===
    
    async def create_table_or_collection(self, name: str, schema: Dict[str, Any] = None) -> bool:
        """Create PostgreSQL table with schema"""
        try:
            async with self.connection_pool.acquire() as conn:
                if schema:
                    # Build CREATE TABLE statement from schema
                    columns = []
                    for column_name, column_def in schema.get('columns', {}).items():
                        column_type = column_def.get('type', 'TEXT')
                        nullable = '' if column_def.get('nullable', True) else 'NOT NULL'
                        default = f"DEFAULT {column_def['default']}" if 'default' in column_def else ''
                        primary_key = 'PRIMARY KEY' if column_def.get('primary_key', False) else ''
                        
                        column_parts = [column_name, column_type, nullable, default, primary_key]
                        columns.append(' '.join(filter(None, column_parts)))
                    
                    # Add constraints
                    constraints = []
                    for constraint in schema.get('constraints', []):
                        constraints.append(constraint)
                    
                    all_definitions = columns + constraints
                    create_sql = f"CREATE TABLE {name} ({', '.join(all_definitions)})"
                else:
                    # Basic table creation
                    create_sql = f"CREATE TABLE {name} (id SERIAL PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                
                await conn.execute(create_sql)
                logger.info(f"Table '{name}' created successfully")
                return True
                
        except Exception as e:
            logger.error(f"Error creating table '{name}': {e}")
            return False
    
    async def drop_table_or_collection(self, name: str) -> bool:
        """Drop PostgreSQL table"""
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute(f'DROP TABLE IF EXISTS {name}')
                logger.info(f"Table '{name}' dropped successfully")
                return True
        except Exception as e:
            logger.error(f"Error dropping table '{name}': {e}")
            return False
    
    async def list_tables_or_collections(self) -> List[str]:
        """List all PostgreSQL tables"""
        try:
            async with self.connection_pool.acquire() as conn:
                results = await conn.fetch(
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
                )
                return [row['table_name'] for row in results]
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            return []
    
    async def get_schema(self, table_or_collection: str) -> Dict[str, Any]:
        """Get PostgreSQL table schema information"""
        try:
            async with self.connection_pool.acquire() as conn:
                # Get column information
                columns_query = """
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable, 
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns 
                WHERE table_name = $1 AND table_schema = 'public'
                ORDER BY ordinal_position
                """
                columns = await conn.fetch(columns_query, table_or_collection)
                
                # Get constraints
                constraints_query = """
                SELECT 
                    constraint_name, 
                    constraint_type, 
                    column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu 
                    ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_name = $1 AND tc.table_schema = 'public'
                """
                constraints = await conn.fetch(constraints_query, table_or_collection)
                
                # Get indexes
                indexes_query = """
                SELECT 
                    indexname as index_name,
                    indexdef as index_definition
                FROM pg_indexes 
                WHERE tablename = $1 AND schemaname = 'public'
                """
                indexes = await conn.fetch(indexes_query, table_or_collection)
                
                # Get table statistics
                stats_query = "SELECT COUNT(*) as row_count FROM " + table_or_collection
                stats = await conn.fetchrow(stats_query)
                
                return {
                    'table_name': table_or_collection,
                    'columns': [dict(col) for col in columns],
                    'constraints': [dict(const) for const in constraints],
                    'indexes': [dict(idx) for idx in indexes],
                    'row_count': stats['row_count'] if stats else 0
                }
                
        except Exception as e:
            logger.error(f"Error getting schema for table '{table_or_collection}': {e}")
            return {}
    
    # === Index Management ===
    
    async def create_index(self, table_or_collection: str, index_spec: Dict[str, Any],
                          options: Dict[str, Any] = None) -> bool:
        """Create PostgreSQL index"""
        try:
            async with self.connection_pool.acquire() as conn:
                index_name = index_spec.get('name', f'idx_{table_or_collection}_{uuid.uuid4().hex[:8]}')
                columns = index_spec.get('columns', [])
                unique = index_spec.get('unique', False)
                method = index_spec.get('method', 'btree')  # btree, hash, gist, gin, etc.
                
                unique_clause = 'UNIQUE' if unique else ''
                columns_clause = ', '.join(columns) if isinstance(columns, list) else str(columns)
                
                create_index_sql = f"""
                CREATE {unique_clause} INDEX {index_name} 
                ON {table_or_collection} USING {method} ({columns_clause})
                """
                
                await conn.execute(create_index_sql)
                logger.info(f"Index '{index_name}' created on table '{table_or_collection}'")
                return True
                
        except Exception as e:
            logger.error(f"Error creating index on table '{table_or_collection}': {e}")
            return False
    
    async def drop_index(self, table_or_collection: str, index_name: str) -> bool:
        """Drop PostgreSQL index"""
        try:
            async with self.connection_pool.acquire() as conn:
                await conn.execute(f'DROP INDEX IF EXISTS {index_name}')
                logger.info(f"Index '{index_name}' dropped")
                return True
        except Exception as e:
            logger.error(f"Error dropping index '{index_name}': {e}")
            return False
    
    async def list_indexes(self, table_or_collection: str) -> List[Dict[str, Any]]:
        """List all indexes for PostgreSQL table"""
        try:
            async with self.connection_pool.acquire() as conn:
                indexes_query = """
                SELECT 
                    i.relname as index_name,
                    ix.indisunique as is_unique,
                    ix.indisprimary as is_primary,
                    array_agg(a.attname ORDER BY a.attnum) as columns
                FROM pg_class i
                JOIN pg_index ix ON i.oid = ix.indexrelid
                JOIN pg_class t ON t.oid = ix.indrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                WHERE t.relname = $1
                GROUP BY i.relname, ix.indisunique, ix.indisprimary
                """
                
                results = await conn.fetch(indexes_query, table_or_collection)
                return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Error listing indexes for table '{table_or_collection}': {e}")
            return []
    
    # === Transaction Support ===
    
    async def begin_transaction(self) -> Any:
        """Begin PostgreSQL transaction"""
        try:
            connection = await self.connection_pool.acquire()
            transaction = connection.transaction()
            await transaction.start()
            return {'connection': connection, 'transaction': transaction}
        except Exception as e:
            logger.error(f"Error starting transaction: {e}")
            return None
    
    async def commit_transaction(self, transaction: Any) -> bool:
        """Commit PostgreSQL transaction"""
        try:
            await transaction['transaction'].commit()
            await self.connection_pool.release(transaction['connection'])
            return True
        except Exception as e:
            logger.error(f"Error committing transaction: {e}")
            return False
    
    async def rollback_transaction(self, transaction: Any) -> bool:
        """Rollback PostgreSQL transaction"""
        try:
            await transaction['transaction'].rollback()
            await self.connection_pool.release(transaction['connection'])
            return True
        except Exception as e:
            logger.error(f"Error rolling back transaction: {e}")
            return False
    
    # === Backup and Recovery ===
    
    async def create_backup(self, backup_config: Dict[str, Any]) -> BackupInfo:
        """Create PostgreSQL backup using pg_dump"""
        start_time = datetime.utcnow()
        backup_id = str(uuid.uuid4())
        
        try:
            # This is a simplified backup - in production, use pg_dump
            backup_location = backup_config.get('location', f'/tmp/pg_backup_{backup_id}.sql')
            
            # Get database size for backup info
            async with self.connection_pool.acquire() as conn:
                size_result = await conn.fetchrow(
                    'SELECT pg_database_size($1) as size_bytes',
                    self.config.database_name
                )
                size_bytes = size_result['size_bytes'] if size_result else 0
            
            end_time = datetime.utcnow()
            duration_ms = (end_time - start_time).total_seconds() * 1000
            
            return BackupInfo(
                backup_id=backup_id,
                backup_type='full',
                size_mb=size_bytes / (1024 * 1024),
                location=backup_location,
                timestamp=start_time,
                duration_ms=duration_ms,
                success=True,
                metadata={
                    'database_name': self.config.database_name,
                    'backup_method': 'logical'
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
        """Restore PostgreSQL from backup"""
        try:
            # This would typically use pg_restore
            logger.info(f"Restore operation for backup {backup_info.backup_id} not implemented")
            return False
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return False
    
    async def list_backups(self) -> List[BackupInfo]:
        """List available PostgreSQL backups"""
        # This would typically query a backup storage system
        return []
    
    # === Monitoring and Statistics ===
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get PostgreSQL database statistics"""
        try:
            async with self.connection_pool.acquire() as conn:
                # Database statistics
                db_stats = await conn.fetchrow(
                    """
                    SELECT 
                        pg_database_size($1) as db_size,
                        (SELECT count(*) FROM pg_stat_user_tables) as table_count,
                        (SELECT sum(n_tup_ins) FROM pg_stat_user_tables) as total_inserts,
                        (SELECT sum(n_tup_upd) FROM pg_stat_user_tables) as total_updates,
                        (SELECT sum(n_tup_del) FROM pg_stat_user_tables) as total_deletes
                    """,
                    self.config.database_name
                )
                
                # Connection statistics
                conn_stats = await conn.fetchrow(
                    "SELECT count(*) as active_connections FROM pg_stat_activity"
                )
                
                return {
                    'database_name': self.config.database_name,
                    'database_size_bytes': db_stats['db_size'] if db_stats else 0,
                    'database_size_mb': (db_stats['db_size'] / (1024 * 1024)) if db_stats and db_stats['db_size'] else 0,
                    'table_count': db_stats['table_count'] if db_stats else 0,
                    'total_inserts': db_stats['total_inserts'] if db_stats else 0,
                    'total_updates': db_stats['total_updates'] if db_stats else 0,
                    'total_deletes': db_stats['total_deletes'] if db_stats else 0,
                    'active_connections': conn_stats['active_connections'] if conn_stats else 0
                }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get PostgreSQL performance metrics"""
        try:
            async with self.connection_pool.acquire() as conn:
                # Table statistics
                table_stats = await conn.fetch(
                    """
                    SELECT 
                        schemaname,
                        tablename,
                        seq_scan,
                        seq_tup_read,
                        idx_scan,
                        idx_tup_fetch,
                        n_tup_ins,
                        n_tup_upd,
                        n_tup_del
                    FROM pg_stat_user_tables
                    """
                )
                
                # Index statistics
                index_stats = await conn.fetch(
                    """
                    SELECT 
                        schemaname,
                        tablename,
                        indexname,
                        idx_scan,
                        idx_tup_read,
                        idx_tup_fetch
                    FROM pg_stat_user_indexes
                    """
                )
                
                return {
                    'table_statistics': [dict(row) for row in table_stats],
                    'index_statistics': [dict(row) for row in index_stats]
                }
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def get_slow_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get PostgreSQL slow queries from pg_stat_statements"""
        try:
            async with self.connection_pool.acquire() as conn:
                # Check if pg_stat_statements extension is available
                extension_check = await conn.fetchrow(
                    "SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'"
                )
                
                if not extension_check:
                    logger.warning("pg_stat_statements extension not available")
                    return []
                
                slow_queries = await conn.fetch(
                    """
                    SELECT 
                        query,
                        calls,
                        total_time,
                        mean_time,
                        rows
                    FROM pg_stat_statements 
                    ORDER BY total_time DESC 
                    LIMIT $1
                    """,
                    limit
                )
                
                return [dict(row) for row in slow_queries]
        except Exception as e:
            logger.error(f"Error getting slow queries: {e}")
            return []
    
    # === Streaming Support ===
    
    async def stream_data(self, table_or_collection: str, query: Dict[str, Any] = None,
                         batch_size: int = 1000) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Stream large datasets in batches"""
        try:
            async with self.connection_pool.acquire() as conn:
                # Build WHERE clause
                where_clause = ''
                where_values = []
                if query:
                    where_conditions, where_values = self._build_where_clause(query)
                    where_clause = f'WHERE {where_conditions}' if where_conditions else ''
                
                # Use cursor for streaming
                sql_query = f'SELECT * FROM {table_or_collection} {where_clause}'
                
                async with conn.transaction():
                    await conn.execute(f'DECLARE data_cursor CURSOR FOR {sql_query}', *where_values)
                    
                    while True:
                        batch = await conn.fetch(f'FETCH {batch_size} FROM data_cursor')
                        if not batch:
                            break
                        
                        yield [dict(row) for row in batch]
                
        except Exception as e:
            logger.error(f"Error streaming data from table '{table_or_collection}': {e}")
            yield []
    
    # === Connection Pool Management ===
    
    async def get_pool_stats(self) -> Dict[str, Any]:
        """Get PostgreSQL connection pool statistics"""
        try:
            if self.connection_pool:
                return {
                    'size': self.connection_pool.get_size(),
                    'max_size': self.connection_pool.get_max_size(),
                    'min_size': self.connection_pool.get_min_size(),
                    'idle_size': self.connection_pool.get_idle_size()
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting pool stats: {e}")
            return {}
    
    async def reset_pool(self) -> bool:
        """Reset PostgreSQL connection pool"""
        try:
            if self.connection_pool:
                await self.connection_pool.close()
            
            return await self.connect()
        except Exception as e:
            logger.error(f"Error resetting pool: {e}")
            return False
    
    # === Utility Methods ===
    
    def _build_where_clause(self, query: Dict[str, Any], start_param_index: int = 1) -> tuple:
        """Build WHERE clause from query dictionary"""
        conditions = []
        values = []
        param_index = start_param_index
        
        for field, value in query.items():
            if isinstance(value, dict):
                # Handle operators like {"$gt": 10}, {"$in": [1,2,3]}
                for op, op_value in value.items():
                    if op == '$gt':
                        conditions.append(f'{field} > ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$gte':
                        conditions.append(f'{field} >= ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$lt':
                        conditions.append(f'{field} < ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$lte':
                        conditions.append(f'{field} <= ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$ne':
                        conditions.append(f'{field} != ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$in':
                        placeholders = ', '.join([f'${param_index + i}' for i in range(len(op_value))])
                        conditions.append(f'{field} IN ({placeholders})')
                        values.extend(op_value)
                        param_index += len(op_value)
                    elif op == '$nin':
                        placeholders = ', '.join([f'${param_index + i}' for i in range(len(op_value))])
                        conditions.append(f'{field} NOT IN ({placeholders})')
                        values.extend(op_value)
                        param_index += len(op_value)
                    elif op == '$like':
                        conditions.append(f'{field} LIKE ${param_index}')
                        values.append(op_value)
                        param_index += 1
                    elif op == '$ilike':
                        conditions.append(f'{field} ILIKE ${param_index}')
                        values.append(op_value)
                        param_index += 1
            else:
                # Simple equality
                conditions.append(f'{field} = ${param_index}')
                values.append(value)
                param_index += 1
        
        return ' AND '.join(conditions), values
    
    def _parse_memory_setting(self, memory_str: str) -> float:
        """Parse PostgreSQL memory setting to MB"""
        try:
            if 'MB' in memory_str:
                return float(memory_str.replace('MB', ''))
            elif 'GB' in memory_str:
                return float(memory_str.replace('GB', '')) * 1024
            elif 'kB' in memory_str:
                return float(memory_str.replace('kB', '')) / 1024
            else:
                return 0.0
        except:
            return 0.0
    
    def _parse_affected_rows(self, result_str: str) -> int:
        """Parse affected rows from SQL result string"""
        try:
            # Result strings like "UPDATE 5", "DELETE 10", "INSERT 0 3"
            parts = result_str.split()
            if len(parts) >= 2:
                return int(parts[-1])
            return 0
        except:
            return 0
    
    def _convert_pipeline_to_sql(self, table: str, pipeline: List[Dict[str, Any]]) -> str:
        """Convert aggregation pipeline to SQL (simplified)"""
        # This is a basic implementation - real conversion would be much more complex
        base_query = f"SELECT * FROM {table}"
        
        for stage in pipeline:
            if '$match' in stage:
                # Add WHERE clause
                where_conditions, _ = self._build_where_clause(stage['$match'])
                if where_conditions:
                    base_query += f" WHERE {where_conditions}"
            
            elif '$group' in stage:
                # Add GROUP BY
                group_spec = stage['$group']
                group_by = group_spec.get('_id', '')
                if group_by:
                    base_query = f"SELECT {group_by}, COUNT(*) as count FROM ({base_query}) subq GROUP BY {group_by}"
            
            elif '$sort' in stage:
                # Add ORDER BY
                sort_spec = stage['$sort']
                order_parts = []
                for field, direction in sort_spec.items():
                    order_dir = 'ASC' if direction > 0 else 'DESC'
                    order_parts.append(f'{field} {order_dir}')
                base_query += f" ORDER BY {', '.join(order_parts)}"
            
            elif '$limit' in stage:
                # Add LIMIT
                base_query += f" LIMIT {stage['$limit']}"
        
        return base_query
    
    # === Database-specific Operations ===
    
    async def get_db_specific_operations(self) -> List[str]:
        """Get PostgreSQL-specific operations"""
        return [
            'vacuum_table',
            'analyze_table',
            'reindex_table',
            'explain_query',
            'create_extension',
            'full_text_search',
            'json_operations'
        ]
    
    async def execute_db_specific_operation(self, operation_name: str, 
                                          parameters: Dict[str, Any] = None) -> Any:
        """Execute PostgreSQL-specific operations"""
        parameters = parameters or {}
        
        async with self.connection_pool.acquire() as conn:
            if operation_name == 'vacuum_table':
                table_name = parameters.get('table')
                await conn.execute(f'VACUUM {table_name}')
                return f"VACUUM completed for table {table_name}"
            
            elif operation_name == 'analyze_table':
                table_name = parameters.get('table')
                await conn.execute(f'ANALYZE {table_name}')
                return f"ANALYZE completed for table {table_name}"
            
            elif operation_name == 'reindex_table':
                table_name = parameters.get('table')
                await conn.execute(f'REINDEX TABLE {table_name}')
                return f"REINDEX completed for table {table_name}"
            
            elif operation_name == 'explain_query':
                query = parameters.get('query')
                result = await conn.fetch(f'EXPLAIN ANALYZE {query}')
                return [dict(row) for row in result]
            
            elif operation_name == 'full_text_search':
                table_name = parameters.get('table')
                search_column = parameters.get('column')
                search_text = parameters.get('text')
                
                query = f"""
                SELECT * FROM {table_name} 
                WHERE to_tsvector('english', {search_column}) @@ plainto_tsquery('english', $1)
                """
                result = await conn.fetch(query, search_text)
                return [dict(row) for row in result]
            
            else:
                raise NotImplementedError(f"PostgreSQL operation '{operation_name}' not implemented")
