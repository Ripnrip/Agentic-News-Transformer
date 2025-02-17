from database_agent import DatabaseAgent
from content_generator import ContentGenerationAgent
import json
from datetime import datetime
import os

def test_content_generation():
    """Test the content generation pipeline."""
    
    # Initialize agents
    db_agent = DatabaseAgent()
    content_agent = ContentGenerationAgent(db_agent)
    
    # Test topics
    topics = [
        "AI and machine learning",
        "Latest AI developments",
        "AI in business",
    ]
    
    # Create results directory
    results_dir = "generated_content"
    os.makedirs(results_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Generate and save articles
    for topic in topics:
        print(f"\nGenerating article about: {topic}")
        article = content_agent.generate_article(topic)
        
        # Save to file
        filename = f"{results_dir}/article_{topic.replace(' ', '_')}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(article, f, indent=2)
            
        # Print preview
        print(f"\nGenerated Article Preview:")
        print(f"Headline: {article['headline']}")
        print(f"Intro: {article['intro'][:200]}...")
        print("\nMetadata:")
        print(f"Generated: {article['metadata']['generated_date']}")
        print(f"Sources: {len(article['metadata']['sources'])} articles")
        print(f"Hashtags: {' '.join(article['metadata']['hashtags'])}")
        print(f"Word counts: {article['metadata']['word_counts']}")
        print(f"\nSaved to: {filename}")

if __name__ == "__main__":
    test_content_generation() 