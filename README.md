# Agentic Content Transformer 🎭

An AI-powered pipeline that converts news articles into lip-synced avatar videos automatically.

## Features

- 📰 **News Scraping**: Scrape and parse news articles from any URL
- 📝 **Content Generation**: Generate concise scripts from news content 
- 🎙️ **Audio Generation**: Convert scripts to natural-sounding speech with ElevenLabs
- 👤 **Avatar Animation**: Create lip-synced videos with Sync.so
- 🔄 **Automatic Workflow**: Full pipeline from article URL to final video

## Architecture

![Architecture](https://mermaid.ink/img/pako:eNp1kU1PwzAMhv9KlBOIafuwXnZASGiHSUhIcAgHLzWlIl8qTSui6n83ab-QNvAp9vPasZ1TUBZTyCG3j1ZZ1j4GBKs-9BxeYXH_8PTy_NLwwBuZvVlFMC7YKKYfKrsDnGvXcN_r2_v2_Z6oE5m1XaNuZW-bE3j_OV9uoXTxYCxCZ3sUO0nPk2tGcJGWa-Wkt4qmXLYkU6UKFzqwvBiVzGlw2PwQtHNb4vdj26hB2RfCzspZLHuA_zBnWlzUJBmwQfLUxZhdI5MIPFhpNr0yMThLcQdubU5xOYF9mTHM45IDLNPZdJZCHmO0TiYJRB-TSCXQcJ0JqsNCPCq9biFv0B84Y_-j0eEXDCOm6w?type=png)

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for deployment)
- API keys for:
  - ElevenLabs
  - Sync.so
  - OpenAI
  - AWS (for S3 storage)
  - NewsDataHub (for news search)
  - Cohere (for vector storage)

## Installation

### Using pip

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/agentic-content-transformer.git
   cd agentic-content-transformer
   ```

2. Create a virtual environment (optional but recommended)
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies
   ```bash
   # For production with all dependencies
   pip install -r requirements.txt
   
   # For development with only direct dependencies
   pip install -r requirements-dev.txt
   ```

### Using conda

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/agentic-content-transformer.git
   cd agentic-content-transformer
   ```

2. Create and activate conda environment
   ```bash
   conda env create -f environment.yml
   conda activate news-scraper
   ```

## Quick Start

1. Set up environment variables
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. Run the application
   ```bash
   streamlit run app.py
   ```

3. Access the application at http://localhost:8501

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

- ElevenLabs for the voice synthesis API
- Sync.so for the avatar lip-syncing technology
- OpenAI for the GPT-4 API used in content generation 