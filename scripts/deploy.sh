#!/bin/bash

# DatasetSmith Deployment Script
# Usage: ./scripts/deploy.sh [environment]
# Example: ./scripts/deploy.sh production

set -e

ENVIRONMENT=${1:-development}
echo "🚀 Deploying DatasetSmith to $ENVIRONMENT..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo "Please create a .env file from .env.example"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi

echo -e "${YELLOW}📦 Building Docker images...${NC}"
docker-compose build

echo -e "${YELLOW}🛑 Stopping existing containers...${NC}"
docker-compose down

echo -e "${YELLOW}🚀 Starting services...${NC}"
docker-compose up -d

echo -e "${YELLOW}⏳ Waiting for services to be healthy...${NC}"
sleep 10

# Check health of each service
check_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service is healthy${NC}"
            return 0
        fi
        echo "Waiting for $service... (attempt $attempt/$max_attempts)"
        sleep 2
        attempt=$((attempt + 1))
    done

    echo -e "${RED}❌ $service failed to start${NC}"
    return 1
}

# Check backend health
check_health "Backend" "http://localhost:8000/health"

# Check frontend health
check_health "Frontend" "http://localhost:3001"

# Check Dagster health
check_health "Dagster" "http://localhost:3000"

echo ""
echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo "📊 Services are running:"
echo "  - Frontend:  http://localhost:3001"
echo "  - Backend:   http://localhost:8000"
echo "  - Dagster:   http://localhost:3000"
echo "  - API Docs:  http://localhost:8000/docs"
echo ""
echo "📝 View logs:"
echo "  docker-compose logs -f"
echo ""
echo "🛑 Stop services:"
echo "  docker-compose down"
