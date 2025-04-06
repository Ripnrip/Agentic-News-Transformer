"""Module for collecting and processing news articles about AI."""

# Standard library imports
import asyncio
import json
import os
from asyncio.exceptions import TimeoutError as AsyncTimeoutError
from datetime import datetime, timedelta
from json.decoder import JSONDecodeError
from typing import List, Optional, Dict, Any
import re
import time
from dotenv import load_dotenv

# Third-party imports
import requests
from aiohttp.client_exceptions import ClientError
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
# Commented out due to installation issues
# from pygooglenews import GoogleNews
from requests.exceptions import RequestException

# Local imports
from models import NewsArticle, ArticleContent
from env_validator import validate_conda_env


# Define the NewsCollector class
# Collect news articles from different sources
class NewsCollector:
    """Collect and format news articles from different sources."""

    def __init__(self, newsapi_key: str, linkedin_credentials: Optional[Dict[str, str]] = None):
        """Initialize NewsCollector with API keys and credentials.
        
        Args:
            newsapi_key: API key for NewsAPI
            linkedin_credentials: Optional credentials for LinkedIn API
        """
        self.newsapi_key = newsapi_key
        self.linkedin_credentials = linkedin_credentials
        self.BASE_URL = "https://newsapi.org/v2/everything"

    def format_linkedin_post(self, post: Dict[str, Any]) -> NewsArticle:
        """Format a LinkedIn post into a NewsArticle.
        
        Args:
            post: Dictionary containing LinkedIn post data
            
        Returns:
            NewsArticle: Formatted article
        """
        return NewsArticle(
            title=post.get('commentary', '')[:100],
            link=f"https://www.linkedin.com/feed/update/{post['id']}",
            content=post.get('commentary'),
            source=post['author'].get('name'),
            source_type="linkedin",
            published_date=datetime.fromtimestamp(int(post['created'])/1000),
            engagement={'likes': post['likes'].get('count', 0), 'comments': post['comments'].get('count', 0)},
            author=post['author'].get('name')
        )

    def format_newsapi_article(self, article: Dict[str, Any]) -> NewsArticle:
        """Format a NewsAPI article into a NewsArticle.
        
        Args:
            article: Dictionary containing NewsAPI article data
            
        Returns:
            NewsArticle: Formatted article
        """
        return NewsArticle(
            title=article['title'],
            link=article['url'],
            content=article.get('content'),
            source=article['source'].get('name'),
            source_type="newsapi",
            published_date=datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')),
            author=article.get('author')
        )

    def format_google_article(self, article: Dict[str, Any]) -> NewsArticle:
        """Format a Google News article into a NewsArticle.
        
        Args:
            article: Dictionary containing Google News article data
            
        Returns:
            NewsArticle: Formatted article
        """
        return NewsArticle(
            title=article['title'],
            link=article['link'],
            source='Google News',
            source_type="google",
            published_date=datetime.fromtimestamp(article['published_parsed'].timestamp())
        )
    

# Define the NewsSearchAgent class
# Search and analyze news articles about AI
class NewsSearchAgent:
    """Search and analyze news articles about AI."""
    
    def __init__(self, article_limit: int = 5):
        """Initialize the NewsSearchAgent with article limit.
        
        Args:
            article_limit: Maximum number of articles to fetch per source
        """
        self.article_limit = article_limit
        self.cache_dir = "cache/articles"
        # Create cache directory if it doesn't exist
        os.makedirs(self.cache_dir, exist_ok=True)

    @staticmethod
    def filter_relevant(input_article: Dict) -> bool:
        """Filter for high-quality AI news articles from input."""
        keywords = ['artificial intelligence', 'machine learning', 'AI', 'neural network', 'deep learning']
        title = input_article['title'].lower()
        content = input_article.get('content', '').lower()
        
        # Check if keywords are in title or content
        has_keywords = any(k.lower() in title or k.lower() in content for k in keywords)
        
        # Check if article has substantial content
        has_content = len(input_article.get('content', '')) > 200
        
        return has_keywords and has_content

    @staticmethod
    async def clean_html_content(html_content: str) -> str:
        """Clean HTML content by removing scripts, styles, and other unwanted elements.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            str: Cleaned HTML content
        """
        # Remove all script tags and their contents
        html_content = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', html_content)
        
        # Remove all style tags and their contents
        html_content = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', '', html_content)
        
        # Remove all CSS and JS links
        html_content = re.sub(r'<link[^>]*>', '', html_content)
        
        # Remove inline styles and event handlers
        html_content = re.sub(r' style="[^"]*"', '', html_content)
        html_content = re.sub(r' on\w+="[^"]*"', '', html_content)
        
        # Remove data attributes
        html_content = re.sub(r' data-[^=]*="[^"]*"', '', html_content)
        
        # Remove class and id attributes
        html_content = re.sub(r' class="[^"]*"', '', html_content)
        html_content = re.sub(r' id="[^"]*"', '', html_content)
        
        # Keep only href attributes for links
        html_content = re.sub(r'<a\b[^>]*href="([^"]*)"[^>]*>', r'<a href="\1">', html_content)
        
        # Keep only src and alt attributes for images
        html_content = re.sub(r'<img\b[^>]*src="([^"]*)"[^>]*alt="([^"]*)"[^>]*>', r'<img src="\1" alt="\2">', html_content)
        
        # Remove empty lines and excessive whitespace
        html_content = re.sub(r'\n\s*\n', '\n', html_content)
        html_content = re.sub(r'[ \t]+', ' ', html_content)
        
        return html_content.strip()

    @staticmethod
    def extract_clean_text(html_content: str) -> str:
        """Extract clean text from HTML content, keeping only relevant article text.
        
        Args:
            html_content: Raw HTML content
            
        Returns:
            str: Clean text content
        """
        # First remove all script, style, and other non-content tags
        html_content = re.sub(r'<(script|style|meta|link|iframe|nav|footer|header)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL)
        
        # Remove common non-content elements by class/id patterns
        for pattern in ['advertisement', 'social', 'related', 'comment', 'sidebar', 'menu', 'popup', 'cookie', 'banner']:
            html_content = re.sub(f'<[^>]*(?:class|id)=[^>]*{pattern}[^>]*>.*?</[^>]*>', '', html_content, flags=re.DOTALL|re.IGNORECASE)
        
        # Extract text from remaining paragraphs and headings
        content_elements = re.findall(r'<(?:p|h1|h2|h3|h4|h5|h6|article)[^>]*>(.*?)</(?:p|h1|h2|h3|h4|h5|h6|article)>', html_content, re.DOTALL)
        
        # Clean the extracted text
        clean_text = []
        for element in content_elements:
            # Remove any remaining HTML tags
            text = re.sub(r'<[^>]+>', ' ', element)
            # Convert HTML entities
            text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
            # Remove extra whitespace
            text = ' '.join(text.split())
            if text.strip():
                clean_text.append(text.strip())
        
        return '\n\n'.join(clean_text)

    @staticmethod
    async def parse_article(url: str):
        """Parse a single article URL using Crawl4AI."""
        print(f"\nParsing article from: {url}")
        
        # Skip if it's a Google News URL
        if url.startswith('https://news.google.com'):
            print("Skipping Google News URL - need actual article URL")
            return {
                "markdown": None,
                "html": None,
                "text": "Skipped Google News URL",
                "error": "Need actual article URL"
            }

        browser_config = BrowserConfig(
            headless=True,  # Set to True for container environments
            verbose=True,
            # Remove unsupported direct arguments
        )

        # Create a custom config for the crawler
        config = {
            "wait_until": "networkidle0",
            "timeout": 30000,
            "initial_delay": 3000,
            "retry_delay": 1000,
            "max_retries": 3,
            "dynamic_wait": True,
            # Add browser settings here instead
            "browser_settings": {
                "window_size": (1920, 1080),
                "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
                "args": [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-infobars',
                    '--window-position=0,0',
                    '--ignore-certifcate-errors',
                    '--ignore-certifcate-errors-spki-list',
                    '--disable-dev-shm-usage',
                    '--headless=new'  # Add headless mode for container environments
                ]
            },
            "selectors": {
                "article": "article, .article, .post-content, .entry-content, main",
                "title": "h1, .article-title, .entry-title",
                "content": "article p, .article-content p, .post-content p, .entry-content p",
                "body": "article, .article-body, .post-content, .entry-content"  # Added body selector
            },
            "remove_selectors": [
                "script",
                "style",
                "link[rel='stylesheet']",
                "noscript",
                "iframe",
                ".advertisement",
                ".social-share",
                ".related-articles",
                ".comments",
                ".sidebar",
                "nav",
                "header:not(h1, h2, h3, h4, h5, h6)",
                "footer",
                "[class*='cookie']",
                "[class*='popup']",
                "[class*='banner']",
                # Additional cleanup for body content
                "[class*='share']",
                "[class*='newsletter']",
                "[class*='subscription']",
                "[class*='widget']",
                "[class*='meta']",
                "[class*='author']",
                "[class*='timestamp']",
                "[class*='date']"
            ],
            "keep_selectors": [
                "title",
                "meta[name='description']",
                "article",
                "h1, h2, h3, h4, h5, h6",
                "p",
                "a[href]",  # Keep links
                "img[alt]",  # Keep images with alt text
                "blockquote"
            ],
            # Add content cleaning rules
            "clean_content": {
                "remove_empty_elements": True,
                "unwrap_single_tags": True,
                "preserve_links": True,
                "strip_comments": True,
                "minimal_formatting": True
            }
        }

        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS
        )
        
        try:
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(
                    url=url,
                    config=run_config,
                    custom_config=config
                )
                
                # Clean and extract content
                cleaned_html = None
                body_content = None
                clean_text = None
                
                if hasattr(result, 'html') and result.html:
                    cleaned_html = await NewsSearchAgent.clean_html_content(result.html)
                    clean_text = NewsSearchAgent.extract_clean_text(cleaned_html)
                    
                    # Extract main content (article body)
                    body_match = re.search(r'<article[^>]*>(.*?)</article>', cleaned_html, re.DOTALL)
                    if body_match:
                        body_content = body_match.group(1)
                    else:
                        body_match = re.search(r'<div[^>]*content[^>]*>(.*?)</div>', cleaned_html, re.DOTALL)
                        if body_match:
                            body_content = body_match.group(1)
                
                content = {
                    "markdown": result.markdown if hasattr(result, 'markdown') else None,
                    "html": cleaned_html,
                    "text": clean_text,  # Add the clean text content
                    "body_content": body_content
                }
                
                # Check if we have any valid content
                if (not content["markdown"] or content["markdown"] == "\n") and not content["html"]:
                    print(f"Warning: No content extracted from {url}, retrying with delay...")
                    
                    # Retry with explicit delay
                    await asyncio.sleep(3)  # Wait 3 seconds
                    result = await crawler.arun(
                        url=url,
                        config=run_config,
                        custom_config=config
                    )
                    
                    content = {
                        "markdown": result.markdown if hasattr(result, 'markdown') else None,
                        "html": result.html if hasattr(result, 'html') else None,
                        "text": result.text if hasattr(result, 'text') else None,
                        "body_content": body_content
                    }
                
                # Final check for content
                if (not content["markdown"] or content["markdown"] == "\n") and not content["html"]:
                    return {
                        "markdown": None,
                        "html": None,
                        "text": f"Failed to extract content from {url}. The site might be blocking automated access.",
                        "error": "No content extracted"
                    }
                    
                return content
                
        except (RuntimeError, ClientError) as e:
            print(f"Crawler error for {url}: {str(e)}")
            return {
                "markdown": None,
                "html": None,
                "text": f"Crawler error: {str(e)}",
                "error": str(e)
            }
        except AsyncTimeoutError as e:
            print(f"Timeout error for {url}: {str(e)}")
            return {
                "markdown": None,
                "html": None,
                "text": f"Timeout error: {str(e)}",
                "error": str(e)
            }
        except ValueError as e:
            print(f"Value error for {url}: {str(e)}")
            return {
                "markdown": None,
                "html": None,
                "text": f"Value error: {str(e)}",
                "error": str(e)
            }

    async def parse_articles_batch(self, articles: List[NewsArticle], timeout_minutes: int = 15):
        """Parse multiple articles concurrently with timeout."""
        start_time = datetime.now()
        timeout = timedelta(minutes=timeout_minutes)
        pending_articles = []
        parsed_articles = []
        failed_articles = []

        for article in articles:
            cache_file = os.path.join(self.cache_dir, f"{hash(article.link)}.json")
            
            # Check if article is already cached
            if os.path.exists(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    parsed_article = json.load(f)
                    parsed_articles.append(parsed_article)
                print(f"Loaded from cache: {article.title}")
                continue

            pending_articles.append(article)

        # Process remaining articles
        while pending_articles and datetime.now() - start_time < timeout:
            current_batch = pending_articles[:5]
            pending_articles = pending_articles[5:]
            
            try:
                tasks = [self.parse_article(article.link) for article in current_batch]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for article, result in zip(current_batch, results):
                    if isinstance(result, Exception):
                        print(f"Failed to parse {article.title}: {str(result)}")
                        failed_articles.append({
                            "title": article.title,
                            "link": article.link,
                            "error": str(result)
                        })
                        continue

                    parsed_article = {
                        "title": article.title,
                        "link": article.link,
                        "content": {
                            "markdown": result["markdown"] if isinstance(result, dict) else None,
                            "html": result["html"] if isinstance(result, dict) else None,
                            "text": result["text"] if isinstance(result, dict) else None
                        },
                        "parsed_date": datetime.now().isoformat()
                    }
                    
                    # Cache the successfully parsed article
                    cache_file = os.path.join(self.cache_dir, f"{hash(article.link)}.json")
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(parsed_article, f, indent=2)
                    
                    parsed_articles.append(parsed_article)
                    print(f"Successfully parsed: {article.title}")

            except AsyncTimeoutError as e:
                print(f"Batch timeout error: {str(e)}")
                pending_articles.extend(current_batch)
            except ClientError as e:
                print(f"Network error in batch: {str(e)}")
                pending_articles.extend(current_batch)
            except (IOError, JSONDecodeError) as e:
                print(f"File operation error in batch: {str(e)}")
                pending_articles.extend(current_batch)

            await asyncio.sleep(1)

        # Report on remaining articles if timeout occurred
        if pending_articles:
            print(f"\nTimeout reached after {timeout_minutes} minutes.")
            print(f"Remaining unparsed articles: {len(pending_articles)}")
            for article in pending_articles:
                failed_articles.append({
                    "title": article.title,
                    "link": article.link,
                    "error": "Timeout"
                })

        return {
            "parsed": parsed_articles,
            "failed": failed_articles,
            "total_processed": len(parsed_articles),
            "total_failed": len(failed_articles),
            "timeout_occurred": bool(pending_articles)
        }

    def fetch_and_parse_articles(self, articles: List[NewsArticle], timeout_minutes: int = 15):
        """Fetch and parse articles using Crawl4AI with timeout."""
        return asyncio.run(self.parse_articles_batch(articles, timeout_minutes))

    def fetch_ai_news_from_google(self) -> List[NewsArticle]:
        """Fetch AI news articles from Google News and resolve their actual URLs."""
        # Commented out due to pygooglenews dependency issues
        print("Google News search is disabled due to dependency issues.")
        return []
        
        # Original implementation:
        # gn = GoogleNews(lang='en', country='US')
        # search_results = gn.search('AI')
        # 
        # articles = []
        # print("\nResolving Google News URLs...")
        # 
        # for entry in search_results['entries'][:self.article_limit]:
        #     try:
        #         # First get the redirect URL from Google News
        #         print(f"Following redirect for: {entry['title']}")
        #         response = requests.head(
        #             entry['link'], 
        #             allow_redirects=True, 
        #             timeout=10,
        #             headers={'User-Agent': 'Mozilla/5.0'}  # Add user agent to avoid blocks
        #         )
        #         actual_url = response.url

    def fetch_ai_news_from_newsapi(self) -> List[NewsArticle]:
        """Fetch AI news articles from NewsAPI with full content.
        
        Returns:
            List[NewsArticle]: List of articles from NewsAPI
        """
        load_dotenv()
        API_KEY = os.getenv('NEWS_API_KEY')
        BASE_URL = "https://newsapi.org/v2/everything"

        # Enhanced parameters for better content
        params = {
            'apiKey': API_KEY,
            'q': '(artificial intelligence OR AI) AND (technology OR innovation OR research)',
            'language': 'en',
            'sortBy': 'relevancy',
            'pageSize': self.article_limit,
            'searchIn': 'title,description,content',  # Search in all fields
            # Add high-quality sources
            'domains': 'bbc.com,reuters.com,apnews.com,bloomberg.com,techcrunch.com,theverge.com,wired.com',
            # Exclude certain domains
            'excludeDomains': 'medium.com,wordpress.com,blogspot.com'
        }
        
        try:
            response = requests.get(BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            articles = []
            if data.get('status') == 'ok':
                for article in data.get('articles', []):
                    # Combine description and content for fuller text
                    full_content = article.get('description', '')
                    if article.get('content'):
                        # Remove the "[+XXX chars]" suffix
                        content = re.sub(r'\[\+\d+ chars\]$', '', article.get('content', ''))
                        full_content = f"{full_content}\n\n{content}"

                    articles.append(NewsArticle(
                        title=article.get('title', 'No Title'),
                        link=article.get('url', 'No URL'),
                        content=full_content,
                        source=article['source'].get('name', 'Unknown'),
                        source_type='newsapi',
                        published_date=datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')) if article.get('publishedAt') else None,
                        author=article.get('author'),
                        image_url=article.get('urlToImage')
                    ))
                    
                    print(f"Found article: {article.get('title')} ({len(full_content)} chars)")
                    
            return articles
            
        except RequestException as e:
            print(f"Error fetching from NewsAPI: {str(e)}")
            return []
        except JSONDecodeError as e:
            print(f"Error parsing NewsAPI response: {str(e)}")
            return []

    def _save_to_cache(self, cache_file: str, data: Dict[str, Any]) -> None:
        """Save data to cache file.
        
        Args:
            cache_file: Path to cache file
            data: Data to save
        """
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            print(f"Error saving to cache: {str(e)}")

    def _load_from_cache(self, cache_file: str) -> Optional[Dict[str, Any]]:
        """Load data from cache file.
        
        Args:
            cache_file: Path to cache file
            
        Returns:
            Optional[Dict[str, Any]]: Cached data or None if not found
        """
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, JSONDecodeError) as e:
            print(f"Error loading from cache: {str(e)}")
            return None

    async def enrich_with_full_content(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Enrich articles with full content by scraping the original URLs."""
        enriched_articles = []
        
        for article in articles:
            try:
                parsed = await self.parse_article(article.link)
                if parsed and parsed.get('text'):
                    article.content = parsed['text']
                enriched_articles.append(article)
            except Exception as e:
                print(f"Error enriching article {article.title}: {str(e)}")
                enriched_articles.append(article)  # Keep original even if enrichment fails
                
        return enriched_articles


# Testing

# async def test_news_search():
#     agent = NewsSearchAgent()
#     news = await agent.fetch_ai_news()
    
#     print(f"Total Results: {news['totalResults']}")
#     for article in news['articles'][:5]:  # Show first 5 articles
#         print(f"\nTitle: {article['title']}")
#         print(f"Source: {article['source']['name']}")
#         print(f"Published: {article['publishedAt']}")
#         print(f"URL: {article['url']}")
#         print("-" * 80)

    
    # Run

def main():
    # Validate conda environment
    validate_conda_env()
    
    print("Fetching AI news articles from Google News...")
    google_ai_news = NewsSearchAgent().fetch_ai_news_from_google()
    
    print("\nAI News Articles from Google News:")
    for google_article in google_ai_news:
        print(f"Title: {google_article.title}")
        print(f"Link: {google_article.link}")
    
    print("\nFetching AI news articles from NewsAPI...")
    newsapi_ai_news = NewsSearchAgent().fetch_ai_news_from_newsapi()
    
    print("\nAI News Articles from NewsAPI:")
    for newsapi_article in newsapi_ai_news:
        print(f"Title: {newsapi_article.title}")
        print(f"Link: {newsapi_article.link}")

    print("Total AI News Articles: ", len(google_ai_news) + len(newsapi_ai_news))
    

class NewsAPIClient:
    """Client for interacting with NewsAPI."""
    
    def __init__(self):
        """Initialize NewsAPI client with API key from environment."""
        load_dotenv()
        self.api_key = os.getenv('NEWS_API_KEY')
        self.base_url = "https://newsapi.org/v2"
        
    def fetch_ai_news(self, days_back: int = 7, limit: int = 10) -> List[NewsArticle]:
        """Fetch AI-related news articles using NewsAPI's everything endpoint."""
        params = {
            'apiKey': self.api_key,
            'q': '(artificial intelligence OR AI) AND (technology OR innovation OR research)',
            'language': 'en',
            'sortBy': 'relevancy',
            'pageSize': limit,
            'searchIn': 'title,description,content',  # Search in all fields
            'from': (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
            'to': datetime.now().strftime('%Y-%m-%d'),
            # Add domains for high-quality sources
            'domains': 'bbc.com,reuters.com,apnews.com,bloomberg.com,techcrunch.com',
        }

        try:
            response = requests.get(
                f"{self.base_url}/everything",
                params=params,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('articles', []):
                # Combine description and content for more complete text
                full_content = article.get('description', '')
                if article.get('content'):
                    # Remove the "[+XXX chars]" suffix
                    content = re.sub(r'\[\+\d+ chars\]$', '', article.get('content', ''))
                    full_content = f"{full_content}\n\n{content}"

                articles.append(NewsArticle(
                    title=article['title'],
                    link=article['url'],
                    content=full_content,
                    source=article['source'].get('name', 'Unknown'),
                    source_type='newsapi',
                    published_date=datetime.fromisoformat(article['publishedAt'].replace('Z', '+00:00')),
                    author=article.get('author'),
                    image_url=article.get('urlToImage')
                ))
            
            return articles
            
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
            return []
    

class NewsDataHubClient:
    """Client for interacting with NewsDataHub API."""
    
    def __init__(self):
        """Initialize NewsDataHub client with API key from environment."""
        load_dotenv()
        self.api_key = os.getenv('NEWS_DATA_HUB_KEY')
        if not self.api_key:
            print("Warning: NEWS_DATA_HUB_KEY not found in environment variables")
        else:
            print(f"API Key found: {self.api_key[:5]}...")
        self.base_url = "https://api.newsdatahub.com/v1"
        
    def fetch_ai_news(self, days_back: int = 7, limit: int = 10) -> List[NewsArticle]:
        """Fetch AI-related news articles using NewsDataHub API."""
        params = {
            'q': 'artificial intelligence OR AI',
            'language': 'en',
            'limit': limit
        }

        try:
            url = f"{self.base_url}/news"
            print(f"Requesting from: {url}")
            
            headers = {
                'X-Api-Key': self.api_key
            }
            
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 401:
                print(f"Authentication failed. Please verify your API key.")
                print(f"Response: {response.text}")
                return []
                
            response.raise_for_status()
            data = response.json()
            
            articles = []
            for article in data.get('data', [])[:limit]:
                # Create a structured content object
                content = ArticleContent(
                    text=article.get('content', ''),
                    html=article.get('html', ''),
                    markdown=article.get('markdown', '')
                )

                # Convert pub_date string to datetime
                pub_date = None
                if article.get('pub_date'):
                    try:
                        pub_date = datetime.fromisoformat(article['pub_date'])
                    except ValueError:
                        print(f"Could not parse date: {article['pub_date']}")

                articles.append(NewsArticle(
                    title=article.get('title', 'No Title'),
                    link=article.get('article_link', 'No URL'),
                    content=content,  # Pass the ArticleContent object
                    source=article.get('source_title', 'Unknown'),
                    source_type='newsdatahub',
                    published_date=pub_date,
                    author=article.get('creator'),
                    image_url=article.get('media_url')
                ))
                
                print(f"Found article: {article.get('title')} ({len(str(content))} chars)")
                
            print(f"\nTotal results available: {data.get('total_results', 0)}")
            print(f"Results per page: {data.get('per_page', 0)}")
            if data.get('next_cursor'):
                print(f"Next cursor available: {data['next_cursor']}")
                
            return articles
            
        except RequestException as e:
            print(f"Network error with NewsDataHub: {str(e)}")
            return []
        except Exception as e:
            print(f"Error with NewsDataHub: {str(e)}")
            return []
    