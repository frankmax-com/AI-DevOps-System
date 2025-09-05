#!/bin/bash

# Database Governance Factory - Quick Start Script
# This script helps you get the Database Governance Factory up and running quickly

set -e

echo "🚀 Database Governance Factory - Quick Start"
echo "=============================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if Docker Compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    echo "📝 Creating .env file from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please review and update it with your actual credentials."
fi

# Create necessary directories
echo "📁 Creating necessary directories..."
mkdir -p logs backups monitoring/grafana/dashboards nginx/sites-enabled ssl

# Pull latest images
echo "📥 Pulling latest Docker images..."
docker-compose pull

# Start the infrastructure services first
echo "🏗️  Starting infrastructure services..."
docker-compose up -d governance-mongodb governance-postgresql governance-redis

# Wait for databases to be ready
echo "⏳ Waiting for databases to be ready..."
sleep 30

# Check database health
echo "🔍 Checking database health..."
docker-compose exec governance-mongodb mongosh --eval "db.adminCommand('ping')" || echo "MongoDB not ready yet"
docker-compose exec governance-postgresql pg_isready -U postgres || echo "PostgreSQL not ready yet"
docker-compose exec governance-redis redis-cli ping || echo "Redis not ready yet"

# Start monitoring services
echo "📊 Starting monitoring services..."
docker-compose up -d governance-prometheus governance-grafana governance-jaeger

# Start the main application
echo "🎯 Starting Database Governance Factory..."
docker-compose up -d governance-api

# Start additional services
echo "🔧 Starting additional services..."
docker-compose up -d governance-nginx governance-backup

# Show service status
echo "📋 Service Status:"
docker-compose ps

echo ""
echo "🎉 Database Governance Factory is starting up!"
echo ""
echo "📍 Service URLs:"
echo "   • Governance API:     http://localhost:8080"
echo "   • API Documentation:  http://localhost:8080/docs"
echo "   • Grafana Dashboard:  http://localhost:3000 (admin/governance-grafana-pass)"
echo "   • Prometheus:         http://localhost:9090"
echo "   • Jaeger Tracing:     http://localhost:16686"
echo "   • Kibana:             http://localhost:5601"
echo ""
echo "🔧 Database Connections:"
echo "   • MongoDB:    localhost:27017 (admin/governance-admin-pass)"
echo "   • PostgreSQL: localhost:5432 (postgres/governance-postgres-pass)"
echo "   • Redis:      localhost:6379 (governance-redis-pass)"
echo ""
echo "📝 Next Steps:"
echo "   1. Wait 2-3 minutes for all services to fully start"
echo "   2. Visit http://localhost:8080/health to check API health"
echo "   3. Visit http://localhost:8080/docs to explore the API"
echo "   4. Configure your databases in the .env file"
echo "   5. Register your databases via the API"
echo ""
echo "🛑 To stop all services: docker-compose down"
echo "🔄 To restart services: docker-compose restart"
echo "📊 To view logs: docker-compose logs -f [service-name]"

# Optional: Open browser to API documentation
if command -v open &> /dev/null; then
    echo "🌐 Opening API documentation in browser..."
    sleep 5
    open http://localhost:8080/docs
elif command -v xdg-open &> /dev/null; then
    echo "🌐 Opening API documentation in browser..."
    sleep 5
    xdg-open http://localhost:8080/docs
fi

echo ""
echo "✅ Database Governance Factory startup complete!"
