#!/bin/bash

# Exit on error
set -e

# Load environment variables
source .env

# Check if doctl is installed
if ! command -v doctl &> /dev/null; then
    echo "doctl is not installed. Please install it first."
    echo "For macOS: brew install doctl"
    exit 1
fi

# Check if user is authenticated with DigitalOcean
if ! doctl account get &> /dev/null; then
    echo "You are not authenticated with DigitalOcean. Please run 'doctl auth init' first."
    exit 1
fi

# Build the Docker image
echo "Building Docker image..."
docker build -t newsscraper .

# Tag the image for DigitalOcean Registry
echo "Tagging image for DigitalOcean Registry..."
docker tag newsscraper registry.digitalocean.com/agentic-content-transformer/newsscraper:latest

# Push to DigitalOcean Registry
echo "Pushing to DigitalOcean Registry..."
docker push registry.digitalocean.com/agentic-content-transformer/newsscraper:latest

# Check if app exists
APP_ID=$(doctl apps list --format ID --no-header)
if [ -z "$APP_ID" ]; then
    echo "Creating new app on DigitalOcean App Platform..."
    APP_ID=$(doctl apps create --spec .do/app.yaml --format ID --no-header)
    echo "App created with ID: $APP_ID"
else
    echo "Updating existing app with ID: $APP_ID"
    doctl apps update $APP_ID --spec .do/app.yaml
fi

# Create a new deployment
echo "Creating new deployment..."
doctl apps create-deployment $APP_ID

echo "Deployment initiated. You can check the status with: doctl apps get $APP_ID" 