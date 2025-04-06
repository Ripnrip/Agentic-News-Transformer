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

# Create a new app
echo "Creating new app on DigitalOcean App Platform..."
APP_ID=$(doctl apps create --spec .do/app.yaml --format ID --no-header)
echo "App created with ID: $APP_ID"

# Create a new deployment
echo "Creating new deployment..."
doctl apps create-deployment $APP_ID

echo "Deployment initiated. You can check the status with: doctl apps get $APP_ID" 