// MongoDB Initialization Script for Database Governance Factory
// This script sets up initial collections, indexes, and configuration

// Switch to governance database
db = db.getSiblingDB('governance');

// Create governance collections with validation schemas
db.createCollection('governance_policies', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['policy_id', 'name', 'description', 'applicable_db_types', 'enforcement_level'],
      properties: {
        policy_id: {
          bsonType: 'string',
          description: 'Unique policy identifier'
        },
        name: {
          bsonType: 'string',
          description: 'Policy display name'
        },
        description: {
          bsonType: 'string',
          description: 'Policy description'
        },
        applicable_db_types: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Database types this policy applies to'
        },
        enforcement_level: {
          bsonType: 'string',
          enum: ['warning', 'error', 'blocking'],
          description: 'Policy enforcement level'
        },
        validation_rules: {
          bsonType: 'object',
          description: 'Policy validation rules'
        },
        compliance_frameworks: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Associated compliance frameworks'
        },
        created_at: {
          bsonType: 'date',
          description: 'Policy creation timestamp'
        },
        updated_at: {
          bsonType: 'date',
          description: 'Policy last update timestamp'
        }
      }
    }
  }
});

db.createCollection('database_connections', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['name', 'db_type', 'module_name', 'environment'],
      properties: {
        name: {
          bsonType: 'string',
          description: 'Unique database connection name'
        },
        db_type: {
          bsonType: 'string',
          enum: ['mongodb', 'postgresql', 'redis', 'cosmos_db', 'blob_storage'],
          description: 'Database type'
        },
        module_name: {
          bsonType: 'string',
          description: 'Service or module name'
        },
        environment: {
          bsonType: 'string',
          enum: ['development', 'staging', 'production'],
          description: 'Environment'
        },
        governance_policies: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Applied governance policies'
        },
        compliance_frameworks: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Compliance frameworks'
        },
        status: {
          bsonType: 'string',
          enum: ['active', 'inactive', 'error'],
          description: 'Connection status'
        },
        last_health_check: {
          bsonType: 'date',
          description: 'Last health check timestamp'
        },
        created_at: {
          bsonType: 'date',
          description: 'Connection registration timestamp'
        }
      }
    }
  }
});

db.createCollection('governance_violations', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['violation_id', 'database_name', 'policy_id', 'severity', 'detected_at'],
      properties: {
        violation_id: {
          bsonType: 'string',
          description: 'Unique violation identifier'
        },
        database_name: {
          bsonType: 'string',
          description: 'Database where violation occurred'
        },
        policy_id: {
          bsonType: 'string',
          description: 'Policy that was violated'
        },
        severity: {
          bsonType: 'string',
          enum: ['low', 'medium', 'high', 'critical'],
          description: 'Violation severity'
        },
        description: {
          bsonType: 'string',
          description: 'Violation description'
        },
        detected_at: {
          bsonType: 'date',
          description: 'When violation was detected'
        },
        violation_data: {
          bsonType: 'object',
          description: 'Additional violation data'
        },
        remediation_suggested: {
          bsonType: 'array',
          items: {
            bsonType: 'string'
          },
          description: 'Suggested remediation actions'
        },
        status: {
          bsonType: 'string',
          enum: ['open', 'in_progress', 'resolved', 'ignored'],
          description: 'Violation status'
        },
        resolved_at: {
          bsonType: 'date',
          description: 'When violation was resolved'
        },
        resolved_by: {
          bsonType: 'string',
          description: 'Who resolved the violation'
        }
      }
    }
  }
});

db.createCollection('audit_events', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['event_id', 'event_type', 'timestamp', 'source'],
      properties: {
        event_id: {
          bsonType: 'string',
          description: 'Unique event identifier'
        },
        event_type: {
          bsonType: 'string',
          description: 'Type of audit event'
        },
        timestamp: {
          bsonType: 'date',
          description: 'Event timestamp'
        },
        source: {
          bsonType: 'string',
          description: 'Event source (database, service, etc.)'
        },
        actor: {
          bsonType: 'string',
          description: 'Who or what triggered the event'
        },
        target: {
          bsonType: 'string',
          description: 'Target of the event'
        },
        action: {
          bsonType: 'string',
          description: 'Action performed'
        },
        details: {
          bsonType: 'object',
          description: 'Additional event details'
        },
        compliance_framework: {
          bsonType: 'string',
          description: 'Associated compliance framework'
        }
      }
    }
  }
});

// Create indexes for performance
db.governance_policies.createIndex({ 'policy_id': 1 }, { unique: true });
db.governance_policies.createIndex({ 'applicable_db_types': 1 });
db.governance_policies.createIndex({ 'enforcement_level': 1 });
db.governance_policies.createIndex({ 'compliance_frameworks': 1 });

db.database_connections.createIndex({ 'name': 1 }, { unique: true });
db.database_connections.createIndex({ 'db_type': 1 });
db.database_connections.createIndex({ 'module_name': 1 });
db.database_connections.createIndex({ 'environment': 1 });
db.database_connections.createIndex({ 'status': 1 });

db.governance_violations.createIndex({ 'violation_id': 1 }, { unique: true });
db.governance_violations.createIndex({ 'database_name': 1 });
db.governance_violations.createIndex({ 'policy_id': 1 });
db.governance_violations.createIndex({ 'severity': 1 });
db.governance_violations.createIndex({ 'status': 1 });
db.governance_violations.createIndex({ 'detected_at': -1 });

db.audit_events.createIndex({ 'event_id': 1 }, { unique: true });
db.audit_events.createIndex({ 'event_type': 1 });
db.audit_events.createIndex({ 'timestamp': -1 });
db.audit_events.createIndex({ 'source': 1 });
db.audit_events.createIndex({ 'compliance_framework': 1 });

// Insert default governance policies
db.governance_policies.insertMany([
  {
    policy_id: 'mongodb_schema_validation',
    name: 'MongoDB Schema Validation',
    description: 'Enforce JSON schema validation for MongoDB collections',
    applicable_db_types: ['mongodb'],
    enforcement_level: 'error',
    validation_rules: {
      require_schema: true,
      validate_data_types: true,
      enforce_required_fields: true,
      check_index_coverage: true
    },
    compliance_frameworks: ['SOX', 'GDPR'],
    remediation_actions: [
      'Add JSON schema validation to collections',
      'Create missing indexes',
      'Validate data consistency'
    ],
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    policy_id: 'postgresql_referential_integrity',
    name: 'PostgreSQL Referential Integrity',
    description: 'Enforce foreign key constraints and referential integrity',
    applicable_db_types: ['postgresql'],
    enforcement_level: 'blocking',
    validation_rules: {
      require_foreign_keys: true,
      validate_constraints: true,
      check_orphaned_records: true,
      enforce_not_null: true
    },
    compliance_frameworks: ['SOX', 'HIPAA'],
    remediation_actions: [
      'Add missing foreign key constraints',
      'Clean up orphaned records',
      'Add NOT NULL constraints'
    ],
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    policy_id: 'redis_memory_optimization',
    name: 'Redis Memory Optimization',
    description: 'Optimize Redis memory usage and TTL policies',
    applicable_db_types: ['redis'],
    enforcement_level: 'warning',
    validation_rules: {
      check_memory_usage: true,
      validate_ttl_policies: true,
      monitor_key_patterns: true,
      check_data_structures: true
    },
    compliance_frameworks: ['Performance'],
    remediation_actions: [
      'Set appropriate TTL values',
      'Optimize data structures',
      'Clean up unused keys'
    ],
    created_at: new Date(),
    updated_at: new Date()
  },
  {
    policy_id: 'data_quality_standards',
    name: 'Data Quality Standards',
    description: 'Ensure data quality across all database types',
    applicable_db_types: ['mongodb', 'postgresql', 'redis', 'cosmos_db', 'blob_storage'],
    enforcement_level: 'error',
    validation_rules: {
      check_data_completeness: true,
      validate_data_formats: true,
      detect_duplicates: true,
      check_data_freshness: true
    },
    compliance_frameworks: ['SOX', 'GDPR', 'HIPAA'],
    remediation_actions: [
      'Clean duplicate records',
      'Standardize data formats',
      'Update stale data'
    ],
    created_at: new Date(),
    updated_at: new Date()
  }
]);

// Create database governance user with appropriate permissions
db.createUser({
  user: 'governance_service',
  pwd: 'governance-service-password',
  roles: [
    { role: 'readWrite', db: 'governance' },
    { role: 'dbAdmin', db: 'governance' }
  ]
});

print('Database Governance Factory MongoDB initialization completed successfully!');
print('Created collections: governance_policies, database_connections, governance_violations, audit_events');
print('Created indexes for optimal query performance');
print('Inserted default governance policies');
print('Created governance_service user with appropriate permissions');
