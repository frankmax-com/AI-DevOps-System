#!/bin/bash

# AI DevOps System - Docker Stop Script

echo "🛑 Stopping AI DevOps System..."
echo "================================"

# Stop all services gracefully
echo "📊 Stopping all services..."
docker-compose down

# Optional: Remove volumes (uncomment to reset all data)
# echo "🗑️  Removing volumes..."
# docker-compose down -v

# Optional: Remove images (uncomment to free disk space)
# echo "🗑️  Removing images..."
# docker-compose down --rmi all

echo "✅ AI DevOps System stopped successfully"

# Show remaining containers (should be empty)
echo ""
echo "📋 Remaining containers:"
docker-compose ps
