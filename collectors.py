"""News collection functionality from various sources."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from models import NewsArticle

class NewsCollector:
    """Collect and format news articles from different sources."""

    def __init__(self, newsapi_key: str, linkedin_credentials: Optional[Dict[str, str]] = None):
        """Initialize NewsCollector with API keys and credentials."""
        self.newsapi_key = newsapi_key
        self.linkedin_credentials = linkedin_credentials
        self.BASE_URL = "https://newsapi.org/v2/everything"

    def format_linkedin_post(self, post: Dict[str, Any]) -> NewsArticle:
        """Format a LinkedIn post into a NewsArticle."""
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
        """Format a NewsAPI article into a NewsArticle."""
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
        """Format a Google News article into a NewsArticle."""
        return NewsArticle(
            title=article['title'],
            link=article['link'],
            source='Google News',
            source_type="google",
            published_date=datetime.fromtimestamp(article['published_parsed'].timestamp())
        ) 