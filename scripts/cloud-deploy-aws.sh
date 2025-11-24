#!/bin/bash

# AWS ECS Deployment Script for DatasetSmith
# Prerequisites:
# - AWS CLI configured
# - Docker installed
# - ECR repository created

set -e

# Configuration
AWS_REGION=${AWS_REGION:-us-east-1}
ECR_REGISTRY=${ECR_REGISTRY}
PROJECT_NAME="datasetsmith"
CLUSTER_NAME="${PROJECT_NAME}-cluster"

if [ -z "$ECR_REGISTRY" ]; then
    echo "❌ Error: ECR_REGISTRY environment variable not set"
    echo "Example: export ECR_REGISTRY=123456789.dkr.ecr.us-east-1.amazonaws.com"
    exit 1
fi

echo "🚀 Deploying DatasetSmith to AWS ECS..."
echo "Region: $AWS_REGION"
echo "Registry: $ECR_REGISTRY"

# Login to ECR
echo "🔐 Logging in to ECR..."
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $ECR_REGISTRY

# Build and tag images
echo "📦 Building images..."
docker build -f Dockerfile.backend -t ${PROJECT_NAME}-backend .
docker build -f Dockerfile.frontend -t ${PROJECT_NAME}-frontend .
docker build -f Dockerfile.mcp -t ${PROJECT_NAME}-mcp .

# Tag images for ECR
docker tag ${PROJECT_NAME}-backend:latest ${ECR_REGISTRY}/${PROJECT_NAME}-backend:latest
docker tag ${PROJECT_NAME}-frontend:latest ${ECR_REGISTRY}/${PROJECT_NAME}-frontend:latest
docker tag ${PROJECT_NAME}-mcp:latest ${ECR_REGISTRY}/${PROJECT_NAME}-mcp:latest

# Push images to ECR
echo "⬆️  Pushing images to ECR..."
docker push ${ECR_REGISTRY}/${PROJECT_NAME}-backend:latest
docker push ${ECR_REGISTRY}/${PROJECT_NAME}-frontend:latest
docker push ${ECR_REGISTRY}/${PROJECT_NAME}-mcp:latest

echo "✅ Images pushed successfully!"
echo ""
echo "Next steps:"
echo "1. Create ECS cluster: aws ecs create-cluster --cluster-name $CLUSTER_NAME"
echo "2. Create task definitions using the pushed images"
echo "3. Create ECS services"
echo "4. Configure Application Load Balancer"
echo ""
echo "Or use AWS Console to complete the setup."
