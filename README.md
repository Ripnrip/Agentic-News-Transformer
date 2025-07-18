# Agentic Content Transformer 🎭

An AI-powered pipeline that converts news articles into lip-synced avatar videos automatically.

## Features

- 📰 **News Scraping**: Scrape and parse news articles from any URL
- 📝 **Content Generation**: Generate concise scripts from news content 
- 🎙️ **Audio Generation**: Convert scripts to natural-sounding speech with OpenAI TTS
- 👤 **Avatar Animation**: Create lip-synced videos with Sync.so
- 🔄 **Automatic Workflow**: Full pipeline from article URL to final video
- 🗃️ **Offline RSS Pipeline**: Fetch AI news via RSS, generate OpenAI TTS audio and Sync.so videos,
  optionally upload them to S3 using `offline_news_to_video.py`

## Architecture

![Architecture](https://mermaid.ink/img/pako:eNp1kU1PwzAMhv9KlBOIafuwXnZASGiHSUhIcAgHLzWlIl8qTSui6n83ab-QNvAp9vPasZ1TUBZTyCG3j1ZZ1j4GBKs-9BxeYXH_8PTy_NLwwBuZvVlFMC7YKKYfKrsDnGvXcN_r2_v2_Z6oE5m1XaNuZW-bE3j_OV9uoXTxYCxCZ3sUO0nPk2tGcJGWa-Wkt4qmXLYkU6UKFzqwvBiVzGlw2PwQtHNb4vdj26hB2RfCzspZLHuA_zBnWlzUJBmwQfLUxZhdI5MIPFhpNr0yMThLcQdubU5xOYF9mTHM45IDLNPZdJZCHmO0TiYJRB-TSCXQcJ0JqsNCPCq9biFv0B84Y_-j0eEXDCOm6w?type=png)

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for deployment)
 - API keys for:
  - Sync.so
  - OpenAI
  - AWS (for S3 storage)
  - Cohere (for vector storage)

## Quick Start

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/agentic-content-transformer.git
   cd agentic-content-transformer
   ```

2. Set up environment variables
   ```bash
   cp deployment/.env.example .env
   # Edit .env with your API keys
   ```

3. Run with Docker Compose
   ```bash
   cd deployment
   docker-compose up
   ```

4. Access the application at http://localhost:8501

## Recent Updates

The application has been updated with several enhancements:

1. **Improved S3 Integration**:
   - Added robust S3 file uploading with curl
   - Fixed Content-Type handling for audio files
   - Added proper URL encoding for filenames with spaces

2. **Enhanced Avatar Generation**:
   - Added support for using direct S3 URLs
   - Improved error handling for MIME type issues
   - Added HTTP status code 201 support for job creation

3. **New Testing Tools**:
   - `test_s3_upload.py`: For testing S3 uploads
   - `test_existing_audio.py`: For testing avatar generation with existing audio
   - `test_avatar_audio.py`: For end-to-end testing with test audio

## Troubleshooting

Common issues and solutions:

### S3 Upload Issues

If you encounter "Access Denied" errors:
- Check your AWS credentials
- Ensure your S3 bucket has the proper permissions
- Try using the `test_s3_upload.py` script to diagnose issues

### Avatar Generation Issues

If you see "Unsupported mime type" errors:
- Verify that your audio files have the correct Content-Type (audio/mpeg)
- Try uploading files manually with the curl command
- Use the "Use known working S3 URL" option in the app

For detailed troubleshooting steps, see [SYNC_INTEGRATION.md](SYNC_INTEGRATION.md).

## Deployment Options

### Azure Web App

1. Set up GitHub Actions secrets:
   - `REGISTRY_URL`
   - `REGISTRY_USERNAME`
   - `REGISTRY_PASSWORD`
   - `AZURE_WEBAPP_PUBLISH_PROFILE`

2. Push to main branch to trigger deployment

### Manual Docker Deployment

```bash
# Build the Docker image
docker build -t agentic-content-transformer -f deployment/Dockerfile .

# Run the container
docker run -p 8501:8501 --env-file .env agentic-content-transformer
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

  - Sync.so for the avatar lip-syncing technology
  - OpenAI for the GPT-4 API used in content generation

## Application Interfaces

The system offers two different interfaces for different use cases:

### 1. Content Generator (app.py)

The main application provides a comprehensive pipeline for:
- Processing news articles from URLs or pasted text
- Generating AI-summarized content
 - Creating audio narrations with OpenAI voices
- Optional avatar video generation
- Social media distribution options

**Best for**: Complete end-to-end content transformation with multiple output options

### 2. News to Avatar (news_to_avatar.py)

A specialized interface focused on creating high-quality avatar videos:
- Tabbed interface with specialized workflow for video creation
- Advanced avatar selection and configuration
- Job management system for tracking video generation tasks
- Better error handling and status tracking

**Best for**: Users primarily interested in creating avatar videos with more detailed controls

## Switching Between Interfaces

Both applications provide a convenient "Application Selector" in the sidebar that lets you launch the other interface in a new browser tab. This allows you to:

- Start with the interface that best matches your primary goal
- Switch to the other interface when needed
- Run both interfaces simultaneously in different tabs

## Running Both Applications

To use the complete system effectively, you need both interfaces running simultaneously on different ports:

### Using the provided scripts

We've added convenience scripts to launch both applications with fixed ports:

#### On macOS/Linux:
```bash
# Make the script executable
chmod +x run_both_apps.sh

# Run both applications
./run_both_apps.sh
```

#### On Windows:
```bash
# Run both applications
run_both_apps.bat
```

These scripts will:
1. Start the main Content Generator on port 8501
2. Start the News to Avatar interface on port 8504
3. Open both in your default browser
4. Save logs to separate files for troubleshooting

### Running manually with specific ports

If you prefer to start the applications manually, use these commands:

```bash
# Terminal 1: Start Content Generator
streamlit run app.py --server.port 8501

# Terminal 2: Start News to Avatar
streamlit run news_to_avatar.py --server.port 8504
```

### Troubleshooting Port Conflicts

If you see an error like "Port XXXX is already in use":

1. Find and stop the process using the port:
   ```bash
   # On macOS/Linux
   lsof -i :8501  # Replace with the conflicting port
   kill -9 PID    # Replace PID with the process ID from the output
   
   # On Windows
   netstat -ano | findstr 8501  # Replace with the conflicting port
   taskkill /F /PID PID        # Replace PID with the process ID
   ```

2. Try using different ports:
   ```bash
   streamlit run app.py --server.port 9001
   streamlit run news_to_avatar.py --server.port 9004
   ```

## Getting Started

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Launch the main Content Generator:
```
streamlit run app.py --server.port 8501
```

3. Or launch the News to Avatar interface:
```
streamlit run news_to_avatar.py --server.port 8504
```

## Docker Deployment

For a containerized deployment with all dependencies pre-installed, you can use Docker:

### Quick Start with Docker

1. Navigate to the deployment directory:
```bash
cd deployment
```

2. Run the Docker setup script:
```bash
./run_docker.sh
```

3. This will:
   - Check for a `.env` file (creating one from `.env.example` if needed)
   - Create necessary directories for storing generated content
   - Build the Docker images with all dependencies
   - Prompt you to choose which application to run

4. Access the applications:
   - Content Generator: http://localhost:8501
   - News to Avatar: http://localhost:8502

### Manual Docker Setup

If you prefer to run Docker commands manually:

1. Build the Docker images:
```bash
docker-compose -f deployment/docker-compose.yml build
```

2. Run both applications:
```bash
docker-compose -f deployment/docker-compose.yml up
```

3. Or run just one of them:
```bash
# For Content Generator only
docker-compose -f deployment/docker-compose.yml up content-generator

# For News to Avatar only
docker-compose -f deployment/docker-compose.yml up news-to-avatar
```

## Required API Keys

- The following API keys should be set in your environment variables:
- `OPENAI_API_KEY`: For content and audio generation
- `SYNC_SO_API_KEY`: For avatar video generation
- Optional: `OPENAI_VOICE` to select a specific TTS voice
- AWS credentials for S3 uploads

## Avatars

Place avatar template videos in the `avatars` directory. The default template should be named `default_avatar.mp4`.