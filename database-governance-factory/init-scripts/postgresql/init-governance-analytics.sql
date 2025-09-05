-- PostgreSQL Initialization Script for Database Governance Factory
-- This script sets up initial tables, indexes, and configuration

-- Create governance analytics schema
CREATE SCHEMA IF NOT EXISTS governance_analytics;

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create extension for JSON aggregation
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Database metadata tracking table
CREATE TABLE governance_analytics.database_metadata (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL UNIQUE,
    database_type VARCHAR(50) NOT NULL CHECK (database_type IN ('mongodb', 'postgresql', 'redis', 'cosmos_db', 'blob_storage')),
    module_name VARCHAR(255) NOT NULL,
    environment VARCHAR(50) NOT NULL CHECK (environment IN ('development', 'staging', 'production')),
    connection_string_hash VARCHAR(255), -- Hashed for security
    governance_policies TEXT[], -- Array of policy IDs
    compliance_frameworks TEXT[], -- Array of compliance frameworks
    status VARCHAR(50) DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'error', 'maintenance')),
    last_health_check TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Policy execution history
CREATE TABLE governance_analytics.policy_execution_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    policy_id VARCHAR(255) NOT NULL,
    execution_id VARCHAR(255) NOT NULL,
    execution_status VARCHAR(50) NOT NULL CHECK (execution_status IN ('success', 'warning', 'error', 'blocked')),
    execution_time_ms INTEGER,
    violations_found INTEGER DEFAULT 0,
    remediation_actions_taken TEXT[],
    execution_details JSONB,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Compliance audit results
CREATE TABLE governance_analytics.compliance_audit_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    audit_id VARCHAR(255) NOT NULL UNIQUE,
    audit_type VARCHAR(100) NOT NULL,
    compliance_framework VARCHAR(100) NOT NULL,
    database_name VARCHAR(255),
    overall_score DECIMAL(5,2) CHECK (overall_score >= 0 AND overall_score <= 100),
    violations_critical INTEGER DEFAULT 0,
    violations_high INTEGER DEFAULT 0,
    violations_medium INTEGER DEFAULT 0,
    violations_low INTEGER DEFAULT 0,
    audit_details JSONB,
    recommendations TEXT[],
    auditor VARCHAR(255),
    audit_started_at TIMESTAMP WITH TIME ZONE,
    audit_completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Performance metrics tracking
CREATE TABLE governance_analytics.performance_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    metric_type VARCHAR(100) NOT NULL,
    metric_name VARCHAR(255) NOT NULL,
    metric_value DECIMAL(15,4),
    metric_unit VARCHAR(50),
    threshold_warning DECIMAL(15,4),
    threshold_critical DECIMAL(15,4),
    is_within_threshold BOOLEAN,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Query analysis and optimization recommendations
CREATE TABLE governance_analytics.query_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    query_hash VARCHAR(255) NOT NULL,
    query_type VARCHAR(50),
    execution_count INTEGER DEFAULT 1,
    avg_execution_time_ms DECIMAL(10,2),
    max_execution_time_ms DECIMAL(10,2),
    min_execution_time_ms DECIMAL(10,2),
    rows_examined_avg BIGINT,
    rows_returned_avg BIGINT,
    index_usage JSONB,
    optimization_suggestions TEXT[],
    performance_impact VARCHAR(50) CHECK (performance_impact IN ('low', 'medium', 'high', 'critical')),
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Data quality assessment results
CREATE TABLE governance_analytics.data_quality_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    table_or_collection VARCHAR(255) NOT NULL,
    assessment_type VARCHAR(100) NOT NULL,
    quality_score DECIMAL(5,2) CHECK (quality_score >= 0 AND quality_score <= 100),
    completeness_score DECIMAL(5,2),
    accuracy_score DECIMAL(5,2),
    consistency_score DECIMAL(5,2),
    timeliness_score DECIMAL(5,2),
    validity_score DECIMAL(5,2),
    record_count BIGINT,
    null_count BIGINT,
    duplicate_count BIGINT,
    issues_found JSONB,
    improvement_recommendations TEXT[],
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Cost optimization tracking
CREATE TABLE governance_analytics.cost_optimization (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    current_usage DECIMAL(15,4),
    usage_unit VARCHAR(50),
    cost_estimate DECIMAL(10,2),
    currency VARCHAR(10) DEFAULT 'USD',
    optimization_potential DECIMAL(5,2), -- Percentage
    optimization_actions TEXT[],
    cost_savings_estimate DECIMAL(10,2),
    analysis_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Security assessment results
CREATE TABLE governance_analytics.security_assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    database_name VARCHAR(255) NOT NULL,
    assessment_type VARCHAR(100) NOT NULL,
    security_score DECIMAL(5,2) CHECK (security_score >= 0 AND security_score <= 100),
    vulnerabilities_critical INTEGER DEFAULT 0,
    vulnerabilities_high INTEGER DEFAULT 0,
    vulnerabilities_medium INTEGER DEFAULT 0,
    vulnerabilities_low INTEGER DEFAULT 0,
    encryption_status VARCHAR(50),
    access_control_score DECIMAL(5,2),
    network_security_score DECIMAL(5,2),
    audit_logging_score DECIMAL(5,2),
    security_findings JSONB,
    remediation_priority TEXT[],
    assessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (database_name) REFERENCES governance_analytics.database_metadata(database_name)
);

-- Create indexes for optimal query performance
CREATE INDEX idx_database_metadata_type ON governance_analytics.database_metadata(database_type);
CREATE INDEX idx_database_metadata_module ON governance_analytics.database_metadata(module_name);
CREATE INDEX idx_database_metadata_environment ON governance_analytics.database_metadata(environment);
CREATE INDEX idx_database_metadata_status ON governance_analytics.database_metadata(status);

CREATE INDEX idx_policy_execution_database ON governance_analytics.policy_execution_history(database_name);
CREATE INDEX idx_policy_execution_policy ON governance_analytics.policy_execution_history(policy_id);
CREATE INDEX idx_policy_execution_status ON governance_analytics.policy_execution_history(execution_status);
CREATE INDEX idx_policy_execution_time ON governance_analytics.policy_execution_history(executed_at);

CREATE INDEX idx_compliance_audit_framework ON governance_analytics.compliance_audit_results(compliance_framework);
CREATE INDEX idx_compliance_audit_database ON governance_analytics.compliance_audit_results(database_name);
CREATE INDEX idx_compliance_audit_score ON governance_analytics.compliance_audit_results(overall_score);
CREATE INDEX idx_compliance_audit_time ON governance_analytics.compliance_audit_results(audit_completed_at);

CREATE INDEX idx_performance_metrics_database ON governance_analytics.performance_metrics(database_name);
CREATE INDEX idx_performance_metrics_type ON governance_analytics.performance_metrics(metric_type);
CREATE INDEX idx_performance_metrics_time ON governance_analytics.performance_metrics(collected_at);
CREATE INDEX idx_performance_metrics_threshold ON governance_analytics.performance_metrics(is_within_threshold);

CREATE INDEX idx_query_analysis_database ON governance_analytics.query_analysis(database_name);
CREATE INDEX idx_query_analysis_hash ON governance_analytics.query_analysis(query_hash);
CREATE INDEX idx_query_analysis_impact ON governance_analytics.query_analysis(performance_impact);
CREATE INDEX idx_query_analysis_time ON governance_analytics.query_analysis(last_seen);

CREATE INDEX idx_data_quality_database ON governance_analytics.data_quality_assessments(database_name);
CREATE INDEX idx_data_quality_table ON governance_analytics.data_quality_assessments(table_or_collection);
CREATE INDEX idx_data_quality_score ON governance_analytics.data_quality_assessments(quality_score);
CREATE INDEX idx_data_quality_time ON governance_analytics.data_quality_assessments(assessed_at);

CREATE INDEX idx_cost_optimization_database ON governance_analytics.cost_optimization(database_name);
CREATE INDEX idx_cost_optimization_resource ON governance_analytics.cost_optimization(resource_type);
CREATE INDEX idx_cost_optimization_potential ON governance_analytics.cost_optimization(optimization_potential);
CREATE INDEX idx_cost_optimization_time ON governance_analytics.cost_optimization(analysis_date);

CREATE INDEX idx_security_assessment_database ON governance_analytics.security_assessments(database_name);
CREATE INDEX idx_security_assessment_type ON governance_analytics.security_assessments(assessment_type);
CREATE INDEX idx_security_assessment_score ON governance_analytics.security_assessments(security_score);
CREATE INDEX idx_security_assessment_time ON governance_analytics.security_assessments(assessed_at);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION governance_analytics.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for database_metadata table
CREATE TRIGGER update_database_metadata_updated_at 
    BEFORE UPDATE ON governance_analytics.database_metadata 
    FOR EACH ROW 
    EXECUTE FUNCTION governance_analytics.update_updated_at_column();

-- Create views for common queries
CREATE VIEW governance_analytics.database_health_summary AS
SELECT 
    dm.database_name,
    dm.database_type,
    dm.module_name,
    dm.environment,
    dm.status,
    dm.last_health_check,
    COUNT(peh.id) as total_policy_executions,
    COUNT(CASE WHEN peh.execution_status = 'error' THEN 1 END) as failed_executions,
    AVG(peh.execution_time_ms) as avg_execution_time,
    MAX(car.overall_score) as latest_compliance_score
FROM governance_analytics.database_metadata dm
LEFT JOIN governance_analytics.policy_execution_history peh ON dm.database_name = peh.database_name
LEFT JOIN governance_analytics.compliance_audit_results car ON dm.database_name = car.database_name
GROUP BY dm.database_name, dm.database_type, dm.module_name, dm.environment, dm.status, dm.last_health_check;

CREATE VIEW governance_analytics.compliance_framework_summary AS
SELECT 
    compliance_framework,
    COUNT(DISTINCT database_name) as databases_covered,
    AVG(overall_score) as avg_compliance_score,
    MIN(overall_score) as min_compliance_score,
    MAX(overall_score) as max_compliance_score,
    SUM(violations_critical) as total_critical_violations,
    SUM(violations_high) as total_high_violations,
    MAX(audit_completed_at) as latest_audit
FROM governance_analytics.compliance_audit_results 
GROUP BY compliance_framework;

-- Create governance service user
CREATE USER governance_service WITH PASSWORD 'governance-analytics-password';
GRANT USAGE ON SCHEMA governance_analytics TO governance_service;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA governance_analytics TO governance_service;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA governance_analytics TO governance_service;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA governance_analytics TO governance_service;

-- Grant access to views
GRANT SELECT ON ALL TABLES IN SCHEMA governance_analytics TO governance_service;

-- Insert sample data for testing
INSERT INTO governance_analytics.database_metadata 
(database_name, database_type, module_name, environment, governance_policies, compliance_frameworks, status)
VALUES 
('user_management_mongodb', 'mongodb', 'user-management-service', 'development', 
 ARRAY['mongodb_schema_validation', 'data_quality_standards'], 
 ARRAY['SOX', 'GDPR'], 'active'),
('payment_processing_cosmos', 'cosmos_db', 'payment-processing-service', 'production',
 ARRAY['cosmos_consistency_validation', 'data_quality_standards'],
 ARRAY['SOX', 'PCI_DSS'], 'active'),
('content_management_mongodb', 'mongodb', 'content-management-service', 'development',
 ARRAY['mongodb_schema_validation', 'content_governance'],
 ARRAY['GDPR', 'DMCA'], 'active');

-- Database Governance Factory PostgreSQL initialization completed
SELECT 'Database Governance Factory PostgreSQL initialization completed successfully!' as message;
