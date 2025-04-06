#!/bin/bash

# Configuration
DOCKERHUB_USERNAME="gsinghdev"  # Your Docker Hub username
IMAGE_NAME="agentic-news-transformer"
TAG="latest"

# Full image name
FULL_IMAGE_NAME="$DOCKERHUB_USERNAME/$IMAGE_NAME:$TAG"

# Build the Docker image
echo "Building Docker image..."
docker build -t $FULL_IMAGE_NAME .

# Log in to Docker Hub
echo "Logging in to Docker Hub..."
docker login

# Push the image
echo "Pushing image to Docker Hub..."
docker push $FULL_IMAGE_NAME

echo "Done! Image is available at: $FULL_IMAGE_NAME" 