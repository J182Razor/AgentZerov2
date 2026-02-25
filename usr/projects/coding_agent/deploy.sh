#!/bin/bash
# Deployment script for Content Automation System

set -e

echo "🚀 Deploying Content Automation System..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Build and start containers
echo "📦 Building Docker images..."
docker-compose -f docker/docker-compose.yml build

echo "🔄 Starting containers..."
docker-compose -f docker/docker-compose.yml up -d

echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check health
echo "🏥 Checking service health..."
docker-compose -f docker/docker-compose.yml ps

echo "✅ Deployment complete!"
echo ""
echo "Services:"
echo "  - Content Automation: Running"
echo "  - Redis: http://localhost:6379"
echo "  - N8N: http://localhost:5678 (admin/changeme)"
echo ""
echo "View logs: docker-compose -f docker/docker-compose.yml logs -f"
echo "Stop: docker-compose -f docker/docker-compose.yml down"
