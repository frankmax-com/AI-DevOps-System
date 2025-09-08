#!/bin/bash

# AI DevOps System - Docker Startup Script

echo "🐳 AI DevOps System - Docker Environment Setup"
echo "================================================"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker Desktop first.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ docker-compose not found. Please install Docker Compose.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker Compose is available${NC}"

# Create environment files if they don't exist
echo -e "\n${YELLOW}📋 Setting up environment files...${NC}"

# Controller Service
if [ ! -f "controller-service/.env" ]; then
    cp controller-service/.env.example controller-service/.env
    echo -e "${GREEN}✅ Created controller-service/.env${NC}"
    echo -e "${YELLOW}💡 Edit controller-service/.env with your Azure Key Vault credentials${NC}"
else
    echo -e "${GREEN}✅ controller-service/.env exists${NC}"
fi

# GitHub Governance Factory
if [ ! -f "github-governance-factory/.env" ]; then
    if [ -f "github-governance-factory/.env.example" ]; then
        cp github-governance-factory/.env.example github-governance-factory/.env
        echo -e "${GREEN}✅ Created github-governance-factory/.env${NC}"
    else
        echo -e "${YELLOW}⚠️  github-governance-factory/.env.example not found${NC}"
    fi
fi

# Azure DevOps Governance Factory
if [ ! -f "azure-devops-governance-factory/.env" ]; then
    if [ -f "azure-devops-governance-factory/.env.example" ]; then
        cp azure-devops-governance-factory/.env.example azure-devops-governance-factory/.env
        echo -e "${GREEN}✅ Created azure-devops-governance-factory/.env${NC}"
    else
        echo -e "${YELLOW}⚠️  azure-devops-governance-factory/.env.example not found${NC}"
    fi
fi

# AI Provider Factory
if [ ! -f "ai-provider-factory/.env" ]; then
    if [ -f "ai-provider-factory/.env.example" ]; then
        cp ai-provider-factory/.env.example ai-provider-factory/.env
        echo -e "${GREEN}✅ Created ai-provider-factory/.env${NC}"
    else
        echo -e "${YELLOW}⚠️  ai-provider-factory/.env.example not found${NC}"
    fi
fi

# Database Governance Factory
if [ ! -f "database-governance-factory/.env" ]; then
    if [ -f "database-governance-factory/.env.example" ]; then
        cp database-governance-factory/.env.example database-governance-factory/.env
        echo -e "${GREEN}✅ Created database-governance-factory/.env${NC}"
    else
        echo -e "${YELLOW}⚠️  database-governance-factory/.env.example not found${NC}"
    fi
fi

# Create monitoring directory if it doesn't exist
if [ ! -d "monitoring" ]; then
    mkdir -p monitoring
    echo -e "${GREEN}✅ Created monitoring directory${NC}"
fi

# Start services in order
echo -e "\n${YELLOW}🚀 Starting AI DevOps System...${NC}"

# Step 1: Start core infrastructure
echo -e "\n${YELLOW}📊 Starting core infrastructure (Redis, PostgreSQL, MongoDB)...${NC}"
docker-compose up -d redis postgres mongo

# Wait for databases to be ready
echo -e "${YELLOW}⏳ Waiting for databases to be ready...${NC}"
sleep 10

# Step 2: Start governance factories
echo -e "\n${YELLOW}🏭 Starting governance factories...${NC}"
docker-compose up -d github-governance azure-governance ai-provider database-governance

# Wait for governance factories to be ready
echo -e "${YELLOW}⏳ Waiting for governance factories to start...${NC}"
sleep 15

# Step 3: Start controller service
echo -e "\n${YELLOW}🎯 Starting Controller Service...${NC}"
docker-compose up -d controller-service

# Step 4: Start monitoring
echo -e "\n${YELLOW}📈 Starting monitoring (Prometheus, Grafana)...${NC}"
docker-compose up -d prometheus grafana

# Wait for all services to be ready
echo -e "\n${YELLOW}⏳ Waiting for all services to be ready...${NC}"
sleep 20

# Check service health
echo -e "\n${YELLOW}🔍 Checking service health...${NC}"

services=(
    "Controller Service:8000"
    "GitHub Governance:8001"
    "Azure Governance:8002"
    "AI Provider:8003"
    "Database Governance:8004"
)

all_healthy=true

for service in "${services[@]}"; do
    name=$(echo $service | cut -d':' -f1)
    port=$(echo $service | cut -d':' -f2)
    
    if curl -f -s "http://localhost:$port/health" > /dev/null; then
        echo -e "${GREEN}✅ $name (port $port) - Healthy${NC}"
    else
        echo -e "${RED}❌ $name (port $port) - Not responding${NC}"
        all_healthy=false
    fi
done

# Show final status
echo -e "\n================================================"
if [ "$all_healthy" = true ]; then
    echo -e "${GREEN}🎉 AI DevOps System is ready!${NC}"
else
    echo -e "${YELLOW}⚠️  Some services may still be starting up...${NC}"
fi

echo -e "\n${YELLOW}📋 Service URLs:${NC}"
echo -e "• Controller Service API: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "• GitHub Governance API: ${GREEN}http://localhost:8001/docs${NC}"
echo -e "• Azure Governance API: ${GREEN}http://localhost:8002/docs${NC}"
echo -e "• AI Provider API: ${GREEN}http://localhost:8003/docs${NC}"
echo -e "• Database Governance API: ${GREEN}http://localhost:8004/docs${NC}"
echo -e "• Prometheus: ${GREEN}http://localhost:9091${NC}"
echo -e "• Grafana: ${GREEN}http://localhost:3001${NC} (admin/admin)"

echo -e "\n${YELLOW}📋 Management Commands:${NC}"
echo -e "• View logs: ${GREEN}docker-compose logs -f${NC}"
echo -e "• Stop all: ${GREEN}docker-compose down${NC}"
echo -e "• Restart service: ${GREEN}docker-compose restart <service-name>${NC}"
echo -e "• Check status: ${GREEN}docker-compose ps${NC}"

echo -e "\n${GREEN}🚀 Ready to create AI Agent Startups!${NC}"
