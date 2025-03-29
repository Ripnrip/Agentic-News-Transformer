#!/bin/bash
# Deployment script for Agentic Content Transformer

# Exit on error
set -e

# Function to print colored output
print_color() {
  if [ "$2" = "green" ]; then
    echo -e "\033[32m$1\033[0m"
  elif [ "$2" = "red" ]; then
    echo -e "\033[31m$1\033[0m"
  elif [ "$2" = "yellow" ]; then
    echo -e "\033[33m$1\033[0m"
  else
    echo -e "$1"
  fi
}

# Function to check if commands exist
check_command() {
  if ! command -v $1 &> /dev/null; then
    print_color "Error: $1 is not installed. Please install it before continuing." "red"
    exit 1
  fi
}

# Check requirements
print_color "Checking requirements..." "yellow"
check_command docker
check_command docker-compose

# Navigate to the project root
cd "$(dirname "$0")/../.."
ROOT_DIR=$(pwd)

# Check if .env file exists
if [ ! -f ".env" ]; then
  print_color "Error: .env file not found. Please create it from the example file." "red"
  print_color "Run: cp deployment/.env.example .env" "yellow"
  exit 1
fi

# Prepare deployment
print_color "Starting deployment..." "green"

# Check deployment mode
DEPLOY_MODE=${1:-basic}

if [ "$DEPLOY_MODE" = "https" ]; then
  # HTTPS mode with Nginx
  print_color "Deploying with HTTPS (Nginx)..." "green"
  
  # Check if SSL certificates exist
  if [ ! -f "deployment/ssl/cert.pem" ] || [ ! -f "deployment/ssl/key.pem" ]; then
    print_color "SSL certificates not found. Generating self-signed certificates..." "yellow"
    mkdir -p deployment/ssl
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout deployment/ssl/key.pem -out deployment/ssl/cert.pem \
      -subj "/CN=localhost"
    print_color "Self-signed certificates generated. For production, replace with real certificates." "yellow"
  fi
  
  # Start with HTTPS configuration
  cd deployment
  docker-compose -f docker-compose.with-nginx.yml down
  docker-compose -f docker-compose.with-nginx.yml up -d --build
  cd ..
  
else
  # Basic HTTP mode
  print_color "Deploying with basic HTTP..." "green"
  cd deployment
  docker-compose down
  docker-compose up -d --build
  cd ..
fi

# Check if deployment was successful
if [ $? -eq 0 ]; then
  if [ "$DEPLOY_MODE" = "https" ]; then
    print_color "✅ Deployment successful! Access your application at https://localhost" "green"
  else
    print_color "✅ Deployment successful! Access your application at http://localhost:8501" "green"
  fi
else
  print_color "❌ Deployment failed. Check the logs for more information." "red"
  exit 1
fi 