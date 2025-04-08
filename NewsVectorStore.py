from datetime import datetime, timezone
import os
from typing import List, Dict
from dotenv import load_dotenv
import cohere
import chromadb
from agents import NewsArticle, NewsSearchAgent
from env_validator import validate_conda_env

# Load environment variables from .env file
load_dotenv()

class EmbeddingFunction:
    def __init__(self, co_client):
        self.co = co_client

    def __call__(self, input: List[str]) -> List[List[float]]:
        response = self.co.embed(
            texts=input,
            model="embed-multilingual-v2.0",
            input_type="classification"
        )
        return response.embeddings

class CohereEmbeddingFunction:
    def __init__(self, co_client):
        self.co = co_client

    def __call__(self, input: List[str]) -> List[List[float]]:
        response = self.co.embed(
            texts=input,
            model="embed-multilingual-v2.0",  # Specify the embedding model
            input_type="search_query"  # Specify the input type
        )
        return response.embeddings

class NewsVectorStore:
    def __init__(self, cohere_api_key: str, collection_name: str = "ai_news"):
        """
        Initializes the vector store with Cohere and ChromaDB.
        """
        self.co = cohere.Client(cohere_api_key)
        self.chroma_client = chromadb.Client()
        print(self.co)
        print(self.chroma_client)
        
        # Create the Cohere embedding function
        self.cohere_ef = CohereEmbeddingFunction(self.co)
        print(self.cohere_ef)
        
        # Create or get the collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.cohere_ef
        )
        print(self.collection)

    def cohere_embedding_function(self, input: List[str]) -> List[List[float]]:
        """Create a Cohere embedding function compatible with ChromaDB."""
        response = self.co.embed(
            texts=input,
            model="embed-multilingual-v2.0",  # Specify the embedding model
            input_type="classification"  # Specify the input type
        )
        print(response)
        return response.embeddings
    

    def store_articles(self, articles: List[NewsArticle]):
        try:
            # Check for existing articles by URL hash
            new_ids = [str(hash(a.link)) for a in articles]
            existing_ids = self.collection.get(ids=new_ids)
            
            # Filter out articles that already exist
            new_articles = [
                article for article, article_id in zip(articles, new_ids) 
                if article_id not in existing_ids['ids']
            ]
            
            if not new_articles:
                print("No new articles to store")
                return

            documents = [f"{a.title}\n{a.content}" for a in new_articles]
            metadata = [{
                "source": a.source or "Unknown",
                "source_type": a.source_type or "Unknown",
                "published_date": a.published_date.isoformat() if a.published_date else "1970-01-01T00:00:00Z",
                "author": a.author or "Unknown",
                "link": a.link or "No Link",
                "url": a.link or "No Link",  # Add url field to match search_similar expectations
                "title": a.title or "Untitled"
            } for a in new_articles]
            new_ids = [str(hash(a.link)) for a in new_articles]

            self.collection.add(
                documents=documents,
                metadatas=metadata,
                ids=new_ids
            )
            print(f"Stored {len(new_articles)} new articles")
        except Exception as e:
            print(f"Error storing articles: {e}")

    def search_articles(self, query: str, n_results: int = 5):
        """
        Searches the vector store for articles similar to the query.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            print("*******" + str(results))
            return results
        except Exception as e:
            print(f"Error during search: {e}")
            return []

    def get_similar_articles(self, article: NewsArticle, n_results: int = 5):
        """
        Finds articles similar to the given article.
        """
        try:
            query_text = f"{article.title}\n{article.content}"
            results = self.collection.query(
                query_texts=[query_text],
                n_results=n_results
            )
            print("*******" + str(results))
            return results
        except Exception as e:
            print(f"Error finding similar articles: {e}")
            return []
        

    def get_collection_info(self):
        """List all articles in the collection and their age"""
        # Get all items from collection
        all_items = self.collection.get()
        
        if not all_items['ids']:
            return "Collection is empty"
            
        current_time = datetime.now(timezone.utc)  # Make current_time timezone-aware
        needs_update = False
        
        print(f"Total articles: {len(all_items['ids'])}")
        for i, (id, metadata) in enumerate(zip(all_items['ids'], all_items['metadatas'])):
            print("********" + str(id))
            print("*******" + str(metadata))
            pub_date = datetime.fromisoformat(metadata['published_date'].replace('Z', '+00:00'))  # Ensure pub_date is timezone-aware
            print(pub_date)

            age = current_time - pub_date
            
            if age.total_seconds() < 24 * 3600:  # Less than 24 hours old
                freshness = "FRESH"
            else:
                freshness = "OLD"
                needs_update = True
                
            #print(f"{i+1}. [{freshness}] {metadata['source']} - {pub_date}")
            print(f"** {i+1}. {metadata['source']} - {pub_date}")

            
        return needs_update

    def should_update(self) -> bool:
        """Check if collection needs updating based on newest article age"""
        try:
            # Get newest article
            results = self.collection.get(
                limit=1,
                where={"published_date": {"$gt": "1970"}}#,
                #order_by={"published_date": "desc"}
            )
            
            if not results['ids']:
                return True
            
            newest_date = datetime.fromisoformat(
                results['metadatas'][0]['published_date'].replace('Z', '+00:00')
            )
            age = datetime.now() - newest_date
            
            return age.total_seconds() > 24 * 3600
        except Exception as e:
            print(f"Error during should_update: {e}")
            return True

    # Usage with NewsSearchAgent
    def store_news(self):
        """
        Store news articles in the vector store
        """
        agent = NewsSearchAgent()
        vector_store = NewsVectorStore(cohere_api_key=os.getenv("COHERE_API_KEY"))
        
        # Collect news from all sources
        google_news = agent.fetch_ai_news_from_google()
        newsapi_news = agent.fetch_ai_news_from_newsapi()
        all_news = google_news + newsapi_news
        
        # Store in vector database
        vector_store.store_articles(all_news)
        
        # Example search
        similar_articles = vector_store.search_articles(
            "Latest developments in Large Language Models"
        )
        print("*******" + str(similar_articles))
        return similar_articles

def main():
    # Validate conda environment
    validate_conda_env()
    
    # Initialize and store news articles
    vector_store = NewsVectorStore(cohere_api_key=os.getenv("COHERE_API_KEY"))
    vector_store.store_news()
    vector_store.get_collection_info()

if __name__ == "__main__":
    main()
