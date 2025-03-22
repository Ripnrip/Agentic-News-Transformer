# Agentic Content Transformer

An AI-powered system that collects, processes, and transforms AI news content from various sources.

## Project Overview

This project automatically:
1. Collects AI news articles from various sources (NewsAPI, NewsDataHub)
2. Parses and extracts content from the collected articles
3. Stores articles in a database and vector store for semantic search
4. Generates AI-powered content based on the collected news
5. Can create audio versions of the content using ElevenLabs

## Setup

### Prerequisites
- Python 3.8+
- Required API keys:
  - OpenAI API key
  - Cohere API key
  - NewsAPI key
  - NewsDataHub key
  - ElevenLabs API key (for audio generation)

### Installation

1. Clone the repository
```bash
git clone https://github.com/yourusername/Agentic-Content-Transformer.git
cd Agentic-Content-Transformer
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Install Playwright browsers (required for web scraping)
```bash
playwright install
```

4. Create a `.env` file in the root directory with the following content:
```env
# API Keys
OPENAI_API_KEY=your_openai_api_key_here
COHERE_API_KEY=your_cohere_api_key_here
NEWS_API_KEY=your_news_api_key_here
NEWS_DATA_HUB_KEY=your_news_data_hub_key_here
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here

# Configuration
DEBUG=False
LOG_LEVEL=INFO
```

5. Verify the setup
```bash
python test_setup.py
```

## Usage

### Collect and Process News

```bash
python main.py --limit 5
```

The `--limit` parameter specifies how many articles to fetch from each source.

### Generate Content

```bash
python content_generator.py
```

### Generate Audio from Content

```bash
python audio_generator.py
```

## Project Structure

- `main.py`: Main entry point for collecting and processing news
- `agents.py`: Contains news collection and processing agents
  - `NewsCollector`: Handles article collection from different sources
  - `NewsSearchAgent`: Manages article search and content parsing
  - `NewsAPIClient`: Client for NewsAPI integration
  - `NewsDataHubClient`: Client for NewsDataHub integration
- `database_agent.py`: Handles database operations and vector storage
- `models.py`: Data models for news articles
- `NewsVectorStore.py`: Vector database for semantic search
- `test_setup.py`: Setup verification script

## Dependencies

### Core Dependencies
- `openai>=1.0.0`: For content generation
- `cohere>=4.0.0`: For embeddings and semantic search
- `langchain>=0.1.0`: For AI operations
- `chromadb>=0.4.0`: For vector storage
- `elevenlabs>=0.2.0`: For audio generation
- `streamlit>=1.30.0`: For web interface
- `python-dotenv>=1.0.0`: For environment management
- `newsapi-python>=0.2.7`: For NewsAPI integration
- `requests>=2.31.0`: For HTTP requests

### Langchain Packages
- `langchain-core>=0.1.0`
- `langchain-community>=0.1.0`
- `langchain-cohere>=0.1.0`

### Web Scraping
- `crawl4ai`: For web content extraction
- `playwright`: For browser automation

### Social Media APIs
- `tweepy>=4.14.0`: For Twitter/X
- `facebook-sdk>=3.1.0`: For Facebook
- `linkedin-api>=2.0.0a`: For LinkedIn

### Avatar Generation
- `opencv-python>=4.5.0`
- `numpy>=1.19.0`
- `librosa>=0.8.0`

### Agent Framework
- `pydantic-ai>=0.0.30`

## Output Directories

- `results/`: Contains JSON files with processed article data
- `generated_content/`: Contains AI-generated content
- `generated_audio/`: Contains generated audio files
- `vectorstore/`: Contains vector database files
- `cache/articles/`: Contains cached article content

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 