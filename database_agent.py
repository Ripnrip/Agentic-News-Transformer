"""Database agent for storing and retrieving news articles using Pydantic AI."""
import sqlite3
import hashlib
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.cohere import CohereEmbeddings

# Define model types
class ArticleContent(BaseModel):
    """Model for article content with different formats."""
    text: str = ''
    html: str = ''
    markdown: str = ''

class NewsArticle(BaseModel):
    """Model representing a news article."""
    title: str
    link: str
    content: ArticleContent = Field(default_factory=ArticleContent)
    source: Optional[str] = None
    source_type: str = "web"
    published_date: Optional[datetime] = None
    engagement: Optional[Dict[str, int]] = None
    author: Optional[str] = None
    image_url: Optional[str] = None

class SearchQuery(BaseModel):
    """Model for search queries."""
    query: str
    limit: int = 5
    min_similarity: float = 0.7

class SearchResult(BaseModel):
    """Model for search results."""
    article: NewsArticle
    chunk: str
    similarity_score: float

class StoreResult(BaseModel):
    """Result of storing articles."""
    stored_count: int
    skipped_count: int
    errors: List[str] = Field(default_factory=list)

# Create the agent
db_agent = Agent(
    "openai:gpt-4o",
    deps_type=Any,
    result_type=Any,
    system_prompt="Manage database operations for storing and retrieving news articles."
)

# Default paths
SQLITE_PATH = "news.db"
VECTOR_PATH = "vectorstore"

# Initialize embeddings
embeddings = CohereEmbeddings(
    model="embed-english-v3.0",
    cohere_api_key=os.getenv('COHERE_API_KEY')
)

# Initialize vector store
vectorstore = Chroma(
    persist_directory=VECTOR_PATH,
    embedding_function=embeddings
)

# Initialize SQLite
def _init_sqlite():
    """Initialize SQLite database with required tables."""
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    # Create articles table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source TEXT,
            source_type TEXT NOT NULL,
            published_date TIMESTAMP,
            author TEXT,
            image_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            engagement TEXT
        )
    """)
    
    # Create content table for storing different content formats
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_content (
            article_id TEXT PRIMARY KEY,
            text_content TEXT,
            html_content TEXT,
            markdown_content TEXT,
            FOREIGN KEY (article_id) REFERENCES articles (id)
        )
    """)
    
    conn.commit()
    conn.close()

# Initialize database
_init_sqlite()

@db_agent.tool
def store_article(ctx: RunContext[Any], article: NewsArticle) -> str:
    """
    Store an article in both SQLite and vector store.
    
    Args:
        ctx: Runtime context (not used)
        article: Article to store
        
    Returns:
        ID of the stored article
    """
    # Generate ID from title and link
    article_id = hashlib.md5(f"{article.title}-{article.link}".encode()).hexdigest()
    
    # Store in SQLite
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    # Check if article already exists
    cursor.execute("SELECT id FROM articles WHERE id = ?", (article_id,))
    if cursor.fetchone():
        conn.close()
        return article_id  # Article already exists
    
    # Insert article metadata
    cursor.execute("""
        INSERT INTO articles 
        (id, title, link, source, source_type, published_date, author, image_url, created_at, engagement) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        article_id,
        article.title,
        article.link,
        article.source,
        article.source_type,
        article.published_date.isoformat() if article.published_date else None,
        article.author,
        article.image_url,
        datetime.now().isoformat(),
        json.dumps(article.engagement) if article.engagement else None
    ))
    
    # Insert article content
    cursor.execute("""
        INSERT INTO article_content 
        (article_id, text_content, html_content, markdown_content) 
        VALUES (?, ?, ?, ?)
    """, (
        article_id,
        article.content.text,
        article.content.html,
        article.content.markdown
    ))
    
    conn.commit()
    
    # Store in vector database if text content exists
    if article.content and article.content.text:
        # Split text into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        chunks = text_splitter.split_text(article.content.text)
        
        # Store chunks in vector store with metadata
        metadata_list = [{
            "article_id": article_id,
            "title": article.title,
            "link": article.link,
            "source": article.source or "",
            "source_type": article.source_type
        } for _ in chunks]
        
        vectorstore.add_texts(chunks, metadata_list)
        vectorstore.persist()
    
    conn.close()
    return article_id

@db_agent.tool
def search_similar(ctx: RunContext[Any], query: SearchQuery) -> List[SearchResult]:
    """
    Search for articles similar to the query text.
    
    Args:
        ctx: Runtime context (not used)
        query: Search parameters
        
    Returns:
        List of search results with articles and similarity scores
    """
    # Search in vector store
    docs_and_scores = vectorstore.similarity_search_with_score(
        query.query, 
        k=query.limit
    )
    
    # Filter by similarity threshold
    docs_and_scores = [(doc, score) for doc, score in docs_and_scores if score >= query.min_similarity]
    
    # Get full article data for each result
    results = []
    conn = sqlite3.connect(SQLITE_PATH)
    cursor = conn.cursor()
    
    for doc, score in docs_and_scores:
        article_id = doc.metadata.get("article_id")
        cursor.execute("""
            SELECT a.title, a.link, a.source, a.source_type, a.published_date,
                  a.author, a.image_url, a.created_at, a.engagement,
                  c.text_content, c.html_content, c.markdown_content
            FROM articles a
            LEFT JOIN article_content c ON a.id = c.article_id
            WHERE a.id = ?
        """, (article_id,))
        
        row = cursor.fetchone()
        if row:
            article = NewsArticle(
                title=row[0],
                link=row[1],
                source=row[2],
                source_type=row[3],
                published_date=datetime.fromisoformat(row[4]) if row[4] else None,
                author=row[5],
                image_url=row[6],
                engagement=json.loads(row[8]) if row[8] else None,
                content=ArticleContent(
                    text=row[9] or "",
                    html=row[10] or "",
                    markdown=row[11] or ""
                )
            )
            
            results.append(SearchResult(
                article=article,
                chunk=doc.page_content,
                similarity_score=score
            ))
    
    conn.close()
    return results

# Simple interface functions
def store_articles(articles: List[NewsArticle]) -> StoreResult:
    """Store multiple articles and return results."""
    result = StoreResult(stored_count=0, skipped_count=0)
    
    for article in articles:
        try:
            db_agent.run_sync("Store this article", deps=None, inputs={"article": article})
            result.stored_count += 1
        except Exception as e:
            result.errors.append(f"Error storing {article.title}: {str(e)}")
            result.skipped_count += 1
    
    return result

def search_similar_articles(query_text: str, limit: int = 5) -> List[SearchResult]:
    """Search for articles similar to the query text."""
    query = SearchQuery(query=query_text, limit=limit)
    result = db_agent.run_sync("Find similar articles", deps=None, inputs={"query": query})
    
    if isinstance(result.data, list):
        return result.data
    return [] 