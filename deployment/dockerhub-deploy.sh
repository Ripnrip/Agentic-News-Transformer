#!/bin/bash
# Script to build and push Docker image to Docker Hub

# Exit on error
set -e

# Configuration
DOCKER_USERNAME=${1:-"gsinghdev"}  # Default username, pass as first argument to override
IMAGE_NAME="agentic-content-transformer"
IMAGE_TAG=${2:-"latest"}  # Default tag is latest, pass as second argument to override

# Start message
echo "🐳 Building and pushing Docker image to Docker Hub"
echo "Username: $DOCKER_USERNAME"
echo "Image: $IMAGE_NAME:$IMAGE_TAG"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "❌ Docker is not running. Please start Docker Desktop and try again."
  exit 1
fi

# Login to Docker Hub
echo "🔑 Logging in to Docker Hub..."
docker login

# Full image name with username
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME:$IMAGE_TAG"

# Build the Docker image
echo "🏗️ Building Docker image: $FULL_IMAGE_NAME"
docker build -t "$FULL_IMAGE_NAME" -f deployment/Dockerfile .

# Push to Docker Hub
echo "📤 Pushing image to Docker Hub..."
docker push "$FULL_IMAGE_NAME"

echo "✅ Successfully pushed $FULL_IMAGE_NAME to Docker Hub!"
echo ""
echo "You can now pull this image on any machine with:"
echo "docker pull $FULL_IMAGE_NAME"
echo ""
echo "To run the image:"
echo "docker run -p 8501:8501 --env-file .env $FULL_IMAGE_NAME"
echo ""
echo "For DigitalOcean deployment:"
echo "1. Go to https://cloud.digitalocean.com/apps/new"
echo "2. Select 'Docker Hub' as the source"
echo "3. Enter your repository: $FULL_IMAGE_NAME" 