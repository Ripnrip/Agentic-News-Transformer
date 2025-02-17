from agents import NewsSearchAgent, NewsAPIClient, NewsDataHubClient
from NewsVectorStore import NewsVectorStore
import os
import json
from datetime import datetime
import argparse
from database_agent import DatabaseAgent

def log_article_details(articles, parsed_content):
    """Log detailed information about articles and their parsed content."""
    print("\n=== Article Details ===")
    
    for article, content in zip(articles, parsed_content):
        print("\n-------------------")
        print(f"Title: {article.title}")
        print(f"Source: {article.source}")
        print(f"Published: {article.published_date}")
        print(f"URL: {article.link}")
        print("\nMetadata:")
        print(f"- Source Type: {article.source_type}")
        print(f"- Author: {article.author}")
        if article.engagement:
            print(f"- Engagement: {article.engagement}")
        
        print("\nContent Preview:")
        if content.get("content"):
            if content["content"].get("markdown"):
                print("Markdown content:", content["content"]["markdown"][:500] + "...")
            elif content["content"].get("html"):
                print("HTML content:", content["content"]["html"][:500] + "...")
            elif content["content"].get("text"):
                print("Text content:", content["content"]["text"][:500] + "...")
        print("-------------------\n")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Fetch and parse AI news articles')
    parser.add_argument('--limit', type=int, default=5,
                      help='number of articles to fetch from each source (default: 5)')
    args = parser.parse_args()

    agent = NewsSearchAgent(article_limit=args.limit)
    
    # Initialize clients
    #newsapi_client = NewsAPIClient()
    newsdatahub_client = NewsDataHubClient()
    
    # Fetch from sources
    #google_ai_news = agent.fetch_ai_news_from_google()
    #newsapi_articles = newsapi_client.fetch_ai_news(days_back=7, limit=10)
    newsdatahub_articles = newsdatahub_client.fetch_ai_news(days_back=7, limit=5)
    
    # Combine results
    #all_articles = newsapi_articles + newsdatahub_articles
    # Temporary only using newsdatahub

    all_articles = newsdatahub_articles

    print(f"\nTotal Articles Found: {len(all_articles)}")
    print("\nArticle Sources:")
    #print(f"- NewsAPI: {len(newsapi_articles)}")
    print(f"- NewsDataHub: {len(newsdatahub_articles)}")
    
    # Step 2: Parse the actual article content
    print("\nStep 2: Parsing article content...")
    parsing_results = agent.fetch_and_parse_articles(all_articles, timeout_minutes=15)
    
    # Log detailed information
    log_article_details(all_articles, parsing_results["parsed"])
    
    # Print summary
    print("\n=== Parsing Summary ===")
    print(f"Successfully parsed: {parsing_results['total_processed']}")
    print(f"Failed to parse: {parsing_results['total_failed']}")
    if parsing_results['timeout_occurred']:
        print("Note: Timeout occurred during parsing")
    
    if parsing_results['failed']:
        print("\nFailed Articles:")
        for failed in parsing_results['failed']:
            print(f"- {failed['title']}: {failed['error']}")
    
    # Initialize database agent
    db_agent = DatabaseAgent()
    
    # Store articles
    db_agent.store_articles(all_articles)
    
    # Example search
    similar_articles = db_agent.search_similar("Latest developments in AI and machine learning")
    print("\nSimilar Articles:")
    for result in similar_articles:
        print(f"\nTitle: {result['article']['title']}")
        print(f"Score: {result['similarity_score']:.2f}")
        print(f"Matching chunk: {result['chunk'][:200]}...")
    
    # Store in vector database
    vector_store = NewsVectorStore(cohere_api_key=os.getenv("COHERE_API_KEY"))
    vector_store.store_articles(all_articles)
    
    # Save results to files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = "results"
    os.makedirs(results_dir, exist_ok=True)
    
    # Save successful parses
    output_file = os.path.join(results_dir, f"parsed_articles_{timestamp}.json")
    with open(output_file, "w") as f:
        json.dump(parsing_results["parsed"], f, indent=2)
    print(f"\nParsed articles saved to {output_file}")
    
    # Save failed parses
    if parsing_results['failed']:
        failed_file = os.path.join(results_dir, f"failed_articles_{timestamp}.json")
        with open(failed_file, "w") as f:
            json.dump(parsing_results["failed"], f, indent=2)
        print(f"Failed articles saved to {failed_file}")

if __name__ == "__main__":
    main() 