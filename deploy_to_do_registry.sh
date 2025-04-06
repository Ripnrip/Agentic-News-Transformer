#!/bin/bash

# Configuration
REGISTRY="registry.digitalocean.com"
REGISTRY_NAME="agentic-news-transformer"  # Your registry name on DigitalOcean
IMAGE_NAME="news-scraper"
TAG="latest"

# Full image name
FULL_IMAGE_NAME="$REGISTRY/$REGISTRY_NAME/$IMAGE_NAME:$TAG"

# Build the Docker image
echo "Building Docker image..."
docker build -t $FULL_IMAGE_NAME .

# Log in to DigitalOcean Container Registry
echo "Logging in to DigitalOcean Container Registry..."
doctl registry login

# Push the image
echo "Pushing image to DigitalOcean Container Registry..."
docker push $FULL_IMAGE_NAME

echo "Done! Image is available at: $FULL_IMAGE_NAME" 