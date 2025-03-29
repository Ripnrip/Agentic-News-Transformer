# Deployment Guide for Agentic Content Transformer

This guide provides comprehensive instructions for deploying the application in various environments.

## Deployment Options

1. **Docker-based deployment** (recommended for production)
2. **Direct deployment** on a server
3. **Streamlit Cloud** deployment (easiest option)
4. **Netlify + Backend API** deployment (alternative approach)

## 1. Docker-based Deployment

### Prerequisites
- Docker and Docker Compose installed
- Domain name (optional for HTTPS)
- API keys for all services

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agentic-content-transformer.git
   cd agentic-content-transformer
   ```

2. Set up environment variables:
   ```bash
   cp deployment/.env.example .env
   # Edit .env with your API keys
   ```

3. Run the deployment script:
   ```bash
   # For HTTP deployment
   ./deployment/scripts/deploy.sh
   
   # For HTTPS deployment with Nginx
   ./deployment/scripts/deploy.sh https
   ```

4. Access your application at:
   - HTTP: http://your-server-ip:8501
   - HTTPS: https://your-domain.com

## 2. Direct Deployment on a Server

### Prerequisites
- Python 3.10+ installed
- pip and virtualenv
- API keys for all services

### Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/agentic-content-transformer.git
   cd agentic-content-transformer
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   ```bash
   cp deployment/.env.example .env
   # Edit .env with your API keys
   
   # Export variables to environment
   export $(grep -v '^#' .env | xargs)
   ```

5. Run the application:
   ```bash
   streamlit run news_to_avatar.py
   ```

6. For production, use a process manager like `systemd` or `supervisor` to keep the app running.

## 3. Streamlit Cloud Deployment

Streamlit Cloud offers the easiest deployment option with free HTTPS and authentication.

### Prerequisites
- GitHub repository
- API keys for all services

### Steps

1. Push your code to GitHub:
   ```bash
   git push origin main
   ```

2. Go to [Streamlit Cloud](https://streamlit.io/cloud) and sign in

3. Click "New app" and select your repository

4. Configure the app:
   - Main file path: `news_to_avatar.py`
   - Add all your API keys as secrets in the Streamlit settings

5. Deploy the app - Streamlit will automatically build and deploy it

6. Your app will be available at `https://share.streamlit.io/yourusername/your-repo-name/main`

## 4. Netlify + Backend API Deployment

This approach separates the frontend and backend, using Netlify for the UI and a separate backend API.

### Prerequisites
- Netlify account
- API hosting service (like Heroku, AWS Lambda, or Azure Functions)
- API keys for all services

### Steps

1. Create a backend API project that provides endpoints for your application

2. Deploy the backend to your chosen platform (Heroku, AWS, etc.)

3. Create a Streamlit frontend that connects to your backend API

4. Deploy to Netlify:
   ```bash
   # Install Netlify CLI
   npm install -g netlify-cli
   
   # Configure build settings in netlify.toml
   # Deploy to Netlify
   netlify deploy --prod
   ```

5. Your app will be available at `https://your-site-name.netlify.app`

## Deployment to Azure Web App

For Azure Web App deployment, follow these steps:

1. Create an Azure Container Registry (ACR)

2. Build and push your Docker image:
   ```bash
   # Login to ACR
   az acr login --name yourRegistry
   
   # Build and tag the image
   docker build -t yourRegistry.azurecr.io/agentic-content-transformer:latest .
   
   # Push the image
   docker push yourRegistry.azurecr.io/agentic-content-transformer:latest
   ```

3. Create an Azure Web App with container settings pointing to your ACR image

4. Configure environment variables in Application Settings

5. Enable managed identity and grant access to ACR

## Troubleshooting Deployment Issues

### Common Issues

- **"No module found" errors**: Check your requirements.txt file is complete
- **API connection errors**: Verify API keys and check network connectivity
- **Docker build fails**: Ensure Docker daemon is running and you have sufficient disk space
- **Audio/video not processing**: Check S3 bucket permissions and connectivity
- **Sync.so API errors**: Verify media URLs are correctly formatted and publicly accessible

### Checking Logs

```bash
# Docker logs
docker logs agentic-content-transformer

# Streamlit logs
tail -f ~/.streamlit/logs/streamlit.log
```

## Security Best Practices

1. **Never commit API keys** to your repository
2. Use environment variables for sensitive information
3. Enable HTTPS in production
4. Implement authentication for your application
5. Regularly update dependencies to patch security vulnerabilities

## Performance Optimization

1. Use caching for computationally expensive operations
2. Configure proper resource limits in Docker
3. Consider using a CDN for static assets
4. Implement database caching if handling large volumes of data 