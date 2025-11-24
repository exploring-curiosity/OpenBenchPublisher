#!/bin/bash

# Railway Deployment Script for DatasetSmith
# Prerequisites:
# - Railway CLI installed: npm i -g @railway/cli
# - Railway account and project created

set -e

echo "🚂 Deploying DatasetSmith to Railway..."

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI not found. Installing..."
    npm i -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging in to Railway..."
railway login

# Link to project (or create new one)
if [ ! -f "railway.json" ]; then
    echo "📝 Creating new Railway project..."
    railway init
else
    echo "📝 Using existing Railway project..."
    railway link
fi

# Set environment variables
echo "⚙️  Setting environment variables..."
echo "Please set these in Railway dashboard:"
echo "  - TAVILY_API_KEY"
echo "  - OPENAI_API_KEY"
echo "  - VOYAGE_API_KEY"
echo "  - MONGODB_URI"
echo "  - MONGODB_DB"
echo "  - OPENAI_MODEL"

# Deploy services
echo "🚀 Deploying services..."

# Backend
echo "Deploying backend..."
railway up --service backend --dockerfile Dockerfile.backend

# Frontend
echo "Deploying frontend..."
railway up --service frontend --dockerfile Dockerfile.frontend

# Dagster
echo "Deploying Dagster..."
railway up --service dagster --dockerfile Dockerfile.backend

# MCP Agent
echo "Deploying MCP Agent..."
railway up --service mcp-agent --dockerfile Dockerfile.mcp

echo "✅ Deployment complete!"
echo ""
echo "🌐 View your deployment:"
railway open
