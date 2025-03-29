# Deployment Guide

This directory contains configuration files for deploying the Agentic Content Transformer application.

## Quick Start

### Basic Deployment (HTTP only)

1. Set up environment variables:
   ```bash
   cp .env.example ../.env
   # Edit .env with your API keys
   ```

2. Run with Docker Compose:
   ```bash
   docker-compose up -d
   ```

3. Access your application at http://localhost:8501

### HTTPS Deployment with Nginx

1. Create an SSL certificate:
   ```bash
   mkdir -p ssl
   # Option 1: For testing, generate a self-signed certificate
   openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout ssl/key.pem -out ssl/cert.pem
   
   # Option 2: For production, use Let's Encrypt or your own certificates
   # Copy your certificates to the ssl directory
   ```

2. Update the domain name in `nginx.conf`:
   ```bash
   # Replace agentic-transformer.your-domain.com with your actual domain name
   ```

3. Run with Nginx:
   ```bash
   docker-compose -f docker-compose.with-nginx.yml up -d
   ```

4. Access your application at https://your-domain.com

## Deployment Options

### Azure Web App

1. Set up GitHub Actions secrets:
   - `REGISTRY_URL` - Your container registry URL (e.g., myacr.azurecr.io)
   - `REGISTRY_USERNAME` - Your container registry username
   - `REGISTRY_PASSWORD` - Your container registry password
   - `AZURE_WEBAPP_PUBLISH_PROFILE` - Your Azure Webapp publish profile (export from Azure Portal)

2. Configure your Azure Web App:
   - Enable HTTPS
   - Set up environment variables in the Azure portal
   - Configure persistent storage for the application data

3. Push to the main branch to trigger automatic deployment

### Manual Deployment to VPS/VM

1. Install Docker and Docker Compose on your server:
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com | sh
   
   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/download/v2.17.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. Copy the deployment files to your server:
   ```bash
   scp -r deployment user@your-server:/path/to/deployment
   ```
   
3. Follow the instructions for HTTP or HTTPS deployment above.

## Advanced Configuration

### Persistent Storage

The application uses Docker volumes for persistent storage:
- `app-data`: Stores generated audio, video files, and job information

### Environment Variables

Required environment variables:
- `ELEVENLABS_API_KEY`: For audio generation
- `SYNC_SO_API_KEY`: For video lip-sync
- `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`: For S3 access
- `OPENAI_API_KEY`: For content generation
- `NEWS_DATA_HUB_KEY`: For news sources
- `COHERE_API_KEY`: For vector search

### Security Considerations

1. Never expose your API keys in public repositories
2. Use HTTPS in production environments
3. Enable proper access controls for your AWS S3 bucket
4. Consider setting up a CDN for larger scale deployments

## Troubleshooting

- **502 Bad Gateway**: Nginx cannot connect to the Streamlit app. Check if the Streamlit container is running.
- **Connection Refused**: Check firewall settings and ensure ports 80/443 are open.
- **API Errors**: Verify your API keys are set correctly in the environment variables.
- **S3 Access Denied**: Check your AWS IAM permissions for the S3 bucket. 