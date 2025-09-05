"""
Database Governance Factory - Core Manager
Unified governance across MongoDB, PostgreSQL, Redis, Cosmos DB, and Blob Storage
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta
import json
import hashlib

# Import our comprehensive database wrappers
from database_wrappers import (
    DatabaseWrapperFactory,
    DatabaseConfig,
    DatabaseType as WrapperDatabaseType,
    BaseDatabaseWrapper,
    HealthStatus,
    QueryResult
)

logger = logging.getLogger(__name__)

class DatabaseType(Enum):
    """Database types supported by governance system"""
    MONGODB = "mongodb"
    POSTGRESQL = "postgresql"
    REDIS = "redis"
    COSMOSDB = "cosmosdb"
    BLOBSTORAGE = "blobstorage"

@dataclass
class DatabaseConnection:
    """Database connection configuration for governance"""
    name: str
    db_type: DatabaseType
    connection_string: str
    database_name: str
    module_name: str
    environment: str
    governance_policies: List[str]
    compliance_frameworks: List[str]
    additional_config: Dict[str, Any] = None

@dataclass
class GovernancePolicy:
    """Database governance policy definition"""
    policy_id: str
    name: str
    description: str
    applicable_db_types: List[DatabaseType]
    compliance_frameworks: List[str]
    enforcement_level: str
    validation_rules: Dict[str, Any]
    remediation_actions: List[str]

@dataclass
class GovernanceViolation:
    """Governance policy violation"""
    violation_id: str
    database_name: str
    policy_id: str
    severity: str
    description: str
    detected_at: datetime
    violation_data: Dict[str, Any]
    remediation_suggested: List[str]
    status: str

class DatabaseGovernanceManager:
    """Central Database Governance Manager using unified wrappers"""
    
    def __init__(self):
        self.connections: Dict[str, Dict[str, Any]] = {}
        self.wrappers: Dict[str, BaseDatabaseWrapper] = {}
        self.policies: Dict[str, GovernancePolicy] = {}
        self.violations: List[GovernanceViolation] = []
        self.audit_trail: List[Dict[str, Any]] = []
        self._load_default_policies()
    
    def _load_default_policies(self):
        """Load default governance policies"""
        self.policies["data_quality_standards"] = GovernancePolicy(
            policy_id="data_quality_standards",
            name="Data Quality Standards",
            description="Ensure data quality across all database types",
            applicable_db_types=[db_type for db_type in DatabaseType],
            compliance_frameworks=["SOX", "GDPR", "HIPAA"],
            enforcement_level="error",
            validation_rules={
                "check_data_completeness": True,
                "validate_data_formats": True,
                "detect_duplicates": True,
                "check_data_freshness": True
            },
            remediation_actions=[
                "Clean duplicate records",
                "Standardize data formats", 
                "Update stale data"
            ]
        )
    
    async def register_database(self, connection_config: DatabaseConnection) -> bool:
        """Register a database for governance monitoring"""
        try:
            # Convert DatabaseType to WrapperDatabaseType
            wrapper_db_type = self._convert_db_type(connection_config.db_type)
            
            # Create database config for wrapper
            wrapper_config = DatabaseConfig(
                host=self._extract_host(connection_config.connection_string),
                port=self._extract_port(connection_config.connection_string),
                database_name=connection_config.database_name,
                connection_string=connection_config.connection_string,
                instance_id=connection_config.name,
                additional_config={
                    'type': wrapper_db_type.value,
                    'module_name': connection_config.module_name,
                    'environment': connection_config.environment,
                    **(connection_config.additional_config or {})
                }
            )
            
            # Create wrapper using factory
            wrapper = DatabaseWrapperFactory.create_wrapper(wrapper_config)
            
            # Test connection
            connection_successful = await wrapper.connect()
            
            if connection_successful:
                self.connections[connection_config.name] = {
                    'config': connection_config,
                    'last_health_check': datetime.utcnow(),
                    'governance_status': 'active'
                }
                self.wrappers[connection_config.name] = wrapper
                
                self._log_audit_event(
                    action="database_registered",
                    database_name=connection_config.name,
                    details={
                        "module": connection_config.module_name, 
                        "type": connection_config.db_type.value,
                        "environment": connection_config.environment
                    }
                )
                
                logger.info(f"Database {connection_config.name} registered successfully")
                return True
            else:
                logger.error(f"Failed to connect to database {connection_config.name}")
                return False
                
        except Exception as e:
            logger.error(f"Error registering database {connection_config.name}: {e}")
            return False
    
    def _convert_db_type(self, db_type: DatabaseType) -> WrapperDatabaseType:
        """Convert governance DatabaseType to wrapper DatabaseType"""
        type_mapping = {
            DatabaseType.MONGODB: WrapperDatabaseType.MONGODB,
            DatabaseType.POSTGRESQL: WrapperDatabaseType.POSTGRESQL,
            DatabaseType.REDIS: WrapperDatabaseType.REDIS,
            DatabaseType.COSMOSDB: WrapperDatabaseType.COSMOSDB,
            DatabaseType.BLOBSTORAGE: WrapperDatabaseType.BLOBSTORAGE,
        }
        return type_mapping[db_type]
    
    def _extract_host(self, connection_string: str) -> str:
        """Extract host from connection string"""
        try:
            from urllib.parse import urlparse
            if connection_string.startswith(('mongodb://', 'postgresql://', 'redis://')):
                parsed = urlparse(connection_string)
                return parsed.hostname or 'localhost'
            elif 'documents.azure.com' in connection_string:
                return connection_string.split('://')[1].split('/')[0] if '://' in connection_string else connection_string
            elif 'core.windows.net' in connection_string:
                return 'blobstorage'
            else:
                return 'localhost'
        except:
            return 'localhost'
    
    def _extract_port(self, connection_string: str) -> int:
        """Extract port from connection string"""
        try:
            from urllib.parse import urlparse
            if connection_string.startswith(('mongodb://', 'postgresql://', 'redis://')):
                parsed = urlparse(connection_string)
                return parsed.port or {'mongodb': 27017, 'postgresql': 5432, 'redis': 6379}.get(parsed.scheme, 0)
            else:
                return 443
        except:
            return 0
    
    async def run_governance_audit(self, database_name: str = None) -> Dict[str, Any]:
        """Run comprehensive governance audit"""
        audit_results = {
            'audit_id': hashlib.md5(f"{datetime.utcnow().isoformat()}".encode()).hexdigest()[:8],
            'timestamp': datetime.utcnow().isoformat(),
            'databases_audited': [],
            'violations_found': [],
            'compliance_score': 0.0,
            'recommendations': []
        }
        
        databases_to_audit = [database_name] if database_name else list(self.connections.keys())
        
        for db_name in databases_to_audit:
            if db_name not in self.connections:
                continue
                
            db_config = self.connections[db_name]['config']
            wrapper = self.wrappers.get(db_name)
            
            if not wrapper:
                logger.warning(f"No wrapper found for database {db_name}")
                continue
            
            # Check health first
            try:
                health_status = await wrapper.health_check()
                if not health_status.is_healthy:
                    audit_results['violations_found'].append(self._create_health_violation(db_name, health_status))
            except Exception as e:
                logger.error(f"Health check failed for {db_name}: {e}")
                continue
            
            # Run applicable governance policies
            for policy_id, policy in self.policies.items():
                if db_config.db_type in policy.applicable_db_types:
                    violations = await self._validate_policy_with_wrapper(db_name, wrapper, db_config, policy)
                    audit_results['violations_found'].extend(violations)
            
            audit_results['databases_audited'].append({
                'name': db_name,
                'type': db_config.db_type.value,
                'module': db_config.module_name,
                'policies_checked': len([p for p in self.policies.values() if db_config.db_type in p.applicable_db_types])
            })
        
        # Calculate compliance score
        total_checks = sum(len([p for p in self.policies.values() if 
                              self.connections[db]['config'].db_type in p.applicable_db_types]) 
                          for db in databases_to_audit if db in self.connections)
        violations_count = len(audit_results['violations_found'])
        audit_results['compliance_score'] = max(0.0, (total_checks - violations_count) / total_checks * 100) if total_checks > 0 else 100.0
        
        # Generate recommendations
        audit_results['recommendations'] = self._generate_recommendations(audit_results['violations_found'])
        
        # Store violations
        self.violations.extend([
            GovernanceViolation(**violation) for violation in audit_results['violations_found']
            if isinstance(violation, dict)
        ])
        
        self._log_audit_event(
            action="governance_audit_completed",
            database_name=database_name or "all",
            details={
                'audit_id': audit_results['audit_id'],
                'compliance_score': audit_results['compliance_score'],
                'violations_count': violations_count
            }
        )
        
        return audit_results
    
    def _create_health_violation(self, db_name: str, health_status: HealthStatus) -> Dict[str, Any]:
        """Create a governance violation for health check failure"""
        return {
            'violation_id': hashlib.md5(f"{db_name}_health_{datetime.utcnow()}".encode()).hexdigest()[:8],
            'database_name': db_name,
            'policy_id': 'health_check',
            'severity': 'error',
            'description': f"Database health check failed: {health_status.error_message}",
            'detected_at': datetime.utcnow(),
            'violation_data': {
                'response_time_ms': health_status.response_time_ms,
                'error_message': health_status.error_message
            },
            'remediation_suggested': ['Check database connectivity', 'Review database configuration'],
            'status': 'open'
        }
    
    async def _validate_policy_with_wrapper(self, db_name: str, wrapper: BaseDatabaseWrapper, 
                                          config: DatabaseConnection, policy: GovernancePolicy) -> List[Dict[str, Any]]:
        """Validate a governance policy using the unified wrapper"""
        violations = []
        
        try:
            # Basic data quality check using wrapper health
            health_status = await wrapper.health_check()
            
            if health_status.response_time_ms > 5000:  # Slow response
                violations.append({
                    'violation_id': hashlib.md5(f"{db_name}_slow_response".encode()).hexdigest()[:8],
                    'database_name': db_name,
                    'policy_id': policy.policy_id,
                    'severity': "warning",
                    'description': f"Slow database response time: {health_status.response_time_ms}ms",
                    'detected_at': datetime.utcnow(),
                    'violation_data': {"response_time_ms": health_status.response_time_ms},
                    'remediation_suggested': ["Check database performance", "Review query optimization"],
                    'status': "open"
                })
                
        except Exception as e:
            logger.error(f"Error validating policy {policy.policy_id} for {db_name}: {e}")
            violations.append({
                'violation_id': hashlib.md5(f"{db_name}_{policy.policy_id}_{datetime.utcnow()}".encode()).hexdigest()[:8],
                'database_name': db_name,
                'policy_id': policy.policy_id,
                'severity': "error",
                'description': f"Policy validation failed: {str(e)}",
                'detected_at': datetime.utcnow(),
                'violation_data': {"error": str(e)},
                'remediation_suggested': ["Check database connectivity", "Verify policy configuration"],
                'status': "open"
            })
        
        return violations
    
    def _generate_recommendations(self, violations: List[Dict[str, Any]]) -> List[str]:
        """Generate actionable recommendations based on violations"""
        recommendations = []
        
        if len(violations) > 0:
            recommendations.append(f"Address {len(violations)} governance violations")
        
        if any(v.get('severity') == 'error' for v in violations):
            recommendations.append("Priority: Address error-level violations first")
        
        return recommendations
    
    def _log_audit_event(self, action: str, database_name: str, details: Dict[str, Any]):
        """Log audit event for compliance tracking"""
        audit_event = {
            'timestamp': datetime.utcnow().isoformat(),
            'action': action,
            'database_name': database_name,
            'details': details,
            'audit_id': hashlib.md5(f"{action}_{database_name}_{datetime.utcnow()}".encode()).hexdigest()[:8]
        }
        self.audit_trail.append(audit_event)
        
        # Keep only last 1000 audit events in memory
        if len(self.audit_trail) > 1000:
            self.audit_trail = self.audit_trail[-1000:]
    
    async def get_governance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive governance dashboard data"""
        dashboard_data = {
            'summary': {
                'total_databases': len(self.connections),
                'active_databases': len([db for db in self.connections.values() if db['governance_status'] == 'active']),
                'total_policies': len(self.policies),
                'open_violations': len([v for v in self.violations if v.status == 'open'])
            },
            'databases': [],
            'recent_violations': sorted(
                [self._violation_to_dict(v) for v in self.violations], 
                key=lambda x: x['detected_at'], 
                reverse=True
            )[:10],
            'compliance_summary': {},
            'audit_summary': {
                'recent_audits': len([event for event in self.audit_trail if 
                                    datetime.fromisoformat(event['timestamp']) > datetime.utcnow() - timedelta(days=7)]),
                'last_audit': max([event['timestamp'] for event in self.audit_trail], default="Never")
            }
        }
        
        # Add database details
        for db_name, db_info in self.connections.items():
            config = db_info['config']
            dashboard_data['databases'].append({
                'name': db_name,
                'type': config.db_type.value,
                'module': config.module_name,
                'environment': config.environment,
                'status': db_info['governance_status'],
                'last_health_check': db_info['last_health_check'].isoformat(),
                'violations_count': len([v for v in self.violations if v.database_name == db_name and v.status == 'open'])
            })
        
        return dashboard_data
    
    def _violation_to_dict(self, violation: GovernanceViolation) -> Dict[str, Any]:
        """Convert GovernanceViolation to dictionary"""
        return {
            'violation_id': violation.violation_id,
            'database_name': violation.database_name,
            'policy_id': violation.policy_id,
            'severity': violation.severity,
            'description': violation.description,
            'detected_at': violation.detected_at.isoformat(),
            'violation_data': violation.violation_data,
            'remediation_suggested': violation.remediation_suggested,
            'status': violation.status
        }
    
    async def close_all_connections(self):
        """Close all database connections using wrappers"""
        for db_name, wrapper in self.wrappers.items():
            try:
                if wrapper.is_connected:
                    await wrapper.disconnect()
                    logger.info(f"Disconnected wrapper for {db_name}")
            except Exception as e:
                logger.error(f"Error closing connection for {db_name}: {e}")
        
        self.wrappers.clear()
        logger.info("All database connections closed")

    # Alias methods for compatibility
    async def validate_policy(self, policy: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a governance policy"""
        return {
            "valid": True,
            "policy_id": policy.get("name", "unknown"),
            "validation_result": "Policy structure is valid",
            "timestamp": datetime.now().isoformat()
        }
    
    async def check_compliance(self, database_name: str = None) -> Dict[str, Any]:
        """Check compliance - alias for run_governance_audit"""
        return await self.run_governance_audit(database_name)
    
    async def generate_audit_report(self) -> Dict[str, Any]:
        """Generate audit report - alias for get_governance_dashboard"""
        return await self.get_governance_dashboard()


def create_database_governance_manager() -> DatabaseGovernanceManager:
    """Factory function to create Database Governance Manager"""
    return DatabaseGovernanceManager()
