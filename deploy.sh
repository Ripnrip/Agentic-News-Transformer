#!/bin/bash

# Exit on error
set -e

# Load environment variables
source .env

# Build the Docker image
echo "Building Docker image..."
docker build -t newsscraper .

# Tag the image for DigitalOcean Registry
echo "Tagging image for DigitalOcean Registry..."
docker tag newsscraper registry.digitalocean.com/agentic-content-transformer/newsscraper:latest

# Push to DigitalOcean Registry
echo "Pushing to DigitalOcean Registry..."
docker push registry.digitalocean.com/agentic-content-transformer/newsscraper:latest

# Deploy to DigitalOcean App Platform
echo "Deploying to DigitalOcean App Platform..."
doctl apps create-deployment your-app-id 