"""Data models for news articles."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Literal, Union
from datetime import datetime

class ArticleContent(BaseModel):
    """Model for article content with different formats."""
    text: str = ''
    html: str = ''
    markdown: str = ''

class NewsArticle(BaseModel):
    """Model representing a news article."""
    title: str
    link: str
    content: Union[str, ArticleContent] = Field(default='', description="Article content in plain text or structured format")
    source: Optional[str] = None
    source_type: Literal["newsapi", "google", "linkedin", "newsdatahub", "manual"] = Field(..., description="Platform source of the article")
    published_date: Optional[datetime] = None
    engagement: Optional[Dict[str, int]] = Field(default=None, description="Engagement metrics like views, likes")
    author: Optional[str] = None
    image_url: Optional[str] = None  # Added field for article image 