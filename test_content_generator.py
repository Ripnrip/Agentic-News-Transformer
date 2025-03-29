from database_agent import DatabaseAgent
from content_generator import generate_article, openai_client
import json
from datetime import datetime
import os
from audio_generator import generate_audio_content
from env_validator import validate_conda_env

def test_content_generation():
    """Test the content generation pipeline."""
    
    # Initialize agents
    db_agent = DatabaseAgent()
    
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
        article = generate_article(topic)
        
        # Save to file
        filename = f"{results_dir}/article_{topic.replace(' ', '_')}_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump(article, f, indent=2)
            
        # Print preview
        print(f"\nGenerated Article Preview:")
        print(f"Headline: {article['headline']}")
        print(f"Intro: {article['intro'][:200]}...")
        print("\nMetadata:")
        print(f"Generated: {article['metadata'].get('generated_date', datetime.now().isoformat())}")
        print(f"Sources: {len(article['metadata'].get('sources', []))}")
        print(f"Hashtags: {' '.join(article['metadata'].get('hashtags', []))}")
        print(f"Word counts: {article['metadata'].get('word_count', 0)}")
        print(f"\nSaved to: {filename}")

        # After generating the article
        print("\nGenerating audio content...")
        audio_content = generate_audio_content(article)
        
        print(f"\nAudio Content Generated:")
        print(f"Audio file: {audio_content['audio_file']}")
        print(f"Script file: {audio_content['script_file']}")
        print(f"SRT file: {audio_content['srt_file']}")
        print(f"Estimated duration: {audio_content['duration']:.1f} seconds")

def test_audio_from_existing():
    """Generate audio from existing articles in generated_content directory."""
    print("\nGenerating audio from existing content...")
    
    # Find all JSON files in generated_content
    content_dir = "generated_content"
    json_files = [f for f in os.listdir(content_dir) if f.endswith('.json')]
    
    for json_file in json_files:
        print(f"\nProcessing: {json_file}")
        
        # Load article content
        with open(os.path.join(content_dir, json_file), 'r') as f:
            article = json.load(f)
        
        # Generate audio content
        audio_content = generate_audio_content(article)
        
        print(f"Audio Content Generated:")
        print(f"Audio file: {audio_content['audio_file']}")
        print(f"Script file: {audio_content['script_file']}")
        print(f"SRT file: {audio_content['srt_file']}")
        print(f"Estimated duration: {audio_content['duration']:.1f} seconds")

def main():
    # Validate conda environment
    validate_conda_env()
    
    # Rest of the code...

if __name__ == "__main__":
    test_content_generation()  # Uncomment to run content generation
    #test_audio_from_existing()  # Run audio generation only 