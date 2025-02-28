"""Database agent for storing and retrieving news articles."""
from typing import List, Dict, Any
import sqlite3
import hashlib
import json
import os
from datetime import datetime

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings.cohere import CohereEmbeddings
from models import NewsArticle, ArticleContent
from langchain_community.vectorstores.utils import filter_complex_metadata

class DatabaseAgent:
    """Agent for managing SQLite and vector storage of news articles."""
    
    def __init__(self, sqlite_path: str = "news.db", vector_path: str = "vectorstore"):
        """Initialize database connections and vector store.
        
        Args:
            sqlite_path: Path to SQLite database
            vector_path: Path to vector store
        """
        self.sqlite_path = sqlite_path
        self.vector_path = vector_path
        
        # Initialize Cohere embeddings with specific model
        self.embeddings = CohereEmbeddings(
            model="embed-english-v3.0",
            cohere_api_key=os.getenv('COHERE_API_KEY')
        )
        
        # Initialize vector store
        self.vectorstore = Chroma(
            persist_directory=vector_path,
            embedding_function=self.embeddings
        )
        
        # Initialize SQLite
        self._init_sqlite()
        
    def _init_sqlite(self):
        """Initialize SQLite database with required tables."""
        conn = sqlite3.connect(self.sqlite_path)
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
        
    def _generate_id(self, article: NewsArticle) -> str:
        """Generate a unique ID for an article based on its content.
        
        Args:
            article: NewsArticle object
            
        Returns:
            str: Unique hash ID
        """
        # Combine unique fields to create hash
        unique_string = f"{article.title}{article.link}{article.source}{article.published_date}"
        return hashlib.sha256(unique_string.encode()).hexdigest()
        
    def _chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Split text into chunks for vector storage.
        
        Args:
            text: Text to split
            metadata: Metadata to include with each chunk
            
        Returns:
            List[Dict[str, Any]]: List of chunks with metadata
        """
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = splitter.split_text(text)
        return [{
            "text": chunk,
            "metadata": {
                **metadata,
                "chunk_index": i,
                "total_chunks": len(chunks)
            }
        } for i, chunk in enumerate(chunks)]
        
    def _prepare_metadata(self, metadata: Dict) -> Dict:
        """Clean metadata to ensure all values are simple types."""
        # Make a copy to avoid modifying the original
        cleaned_metadata = metadata.copy()
        
        # Convert datetime to string if it's not already a string
        if cleaned_metadata.get('published_date'):
            if isinstance(cleaned_metadata['published_date'], datetime):
                cleaned_metadata['published_date'] = cleaned_metadata['published_date'].isoformat()
            elif cleaned_metadata['published_date'] is None:
                cleaned_metadata['published_date'] = ''
        
        # Convert all values to strings and handle None
        cleaned_metadata = {
            k: str(v) if v is not None else ''
            for k, v in cleaned_metadata.items()
        }
        
        # No need to filter since we've already cleaned everything to strings
        return cleaned_metadata

    def store_articles(self, articles: List[NewsArticle]):
        """Store articles in both SQLite and vector store.
        
        Args:
            articles: List of NewsArticle objects to store
        """
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        for article in articles:
            article_id = self._generate_id(article)
            
            # Store in SQLite
            cursor.execute("""
                INSERT OR REPLACE INTO articles 
                (id, title, link, source, source_type, published_date, author, image_url, engagement)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                article_id,
                article.title,
                article.link,
                article.source,
                article.source_type,
                article.published_date,
                article.author,
                article.image_url,
                json.dumps(article.engagement) if article.engagement else None
            ))
            
            # Store content formats
            if isinstance(article.content, ArticleContent):
                cursor.execute("""
                    INSERT OR REPLACE INTO article_content
                    (article_id, text_content, html_content, markdown_content)
                    VALUES (?, ?, ?, ?)
                """, (
                    article_id,
                    article.content.text,
                    article.content.html,
                    article.content.markdown
                ))
                content_for_vector = article.content.text
            else:
                cursor.execute("""
                    INSERT OR REPLACE INTO article_content
                    (article_id, text_content)
                    VALUES (?, ?)
                """, (
                    article_id,
                    article.content
                ))
                content_for_vector = article.content
            
            # Prepare metadata for vector store
            metadata = {
                "article_id": article_id,
                "title": article.title,
                "source": article.source,
                "source_type": article.source_type,
                "published_date": article.published_date.isoformat() if article.published_date else None,
                "link": article.link,
                "author": article.author
            }
            
            # Create chunks and store in vector store
            chunks = self._chunk_text(content_for_vector, metadata)
            for chunk in chunks:
                clean_metadata = self._prepare_metadata(chunk["metadata"])
                
                self.vectorstore.add_texts(
                    texts=[chunk["text"]],
                    metadatas=[clean_metadata]
                )
                
        conn.commit()
        conn.close()
        self.vectorstore.persist()
        
    def search_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for similar articles using vector similarity.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Similar articles with metadata
        """
        results = self.vectorstore.similarity_search_with_relevance_scores(
            query,
            k=limit
        )
        
        # Get full article data from SQLite for each result
        conn = sqlite3.connect(self.sqlite_path)
        cursor = conn.cursor()
        
        enriched_results = []
        for doc, score in results:
            cursor.execute("""
                SELECT a.*, ac.text_content, ac.html_content, ac.markdown_content
                FROM articles a
                LEFT JOIN article_content ac ON a.id = ac.article_id
                WHERE a.id = ?
            """, (doc.metadata["article_id"],))
            
            row = cursor.fetchone()
            if row:
                enriched_results.append({
                    "article": {
                        "id": row[0],
                        "title": row[1],
                        "link": row[2],
                        "source": row[3],
                        "source_type": row[4],
                        "published_date": row[5],
                        "author": row[6],
                        "image_url": row[7],
                        "created_at": row[8],
                        "engagement": json.loads(row[9]) if row[9] else None,
                        "content": {
                            "text": row[10],
                            "html": row[11],
                            "markdown": row[12]
                        }
                    },
                    "chunk": doc.page_content,
                    "similarity_score": score
                })
                
        conn.close()
        return enriched_results 