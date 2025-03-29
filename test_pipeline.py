import os
from datetime import datetime
from openai import OpenAI
from elevenlabs import Voice, VoiceSettings, generate as elevenlabs_generate
from elevenlabs.api import Voices
from env_validator import validate_conda_env

def generate_article(topic: str) -> dict:
    """Generate an article about the given topic."""
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    prompt = f"""
    Generate a clear, accessible article about "{topic}" in an informative tone for a general audience.
    
    The article should be approximately 800 words and include:
    1. An attention-grabbing headline
    2. An engaging introduction
    3. Informative body content 
    4. A concise conclusion
    
    FORMAT:
    Return a JSON object with the following structure:
    {{
        "headline": "The headline",
        "intro": "Introduction paragraph",
        "body": "Main content...",
        "conclusion": "Concluding paragraph"
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    
    return response.choices[0].message.content

def generate_audio(text: str, output_path: str):
    """Generate audio from text using ElevenLabs."""
    voice_settings = VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True
    )
    
    # Get available voices
    voices = Voices.from_api()
    voice = voices[0]  # Use the first available voice
    
    # Generate audio
    audio = elevenlabs_generate(
        text=text,
        voice=voice,
        model="eleven_monolingual_v1"
    )
    
    # Save audio
    with open(output_path, 'wb') as f:
        f.write(audio)

def main():
    # Validate conda environment
    validate_conda_env()
    
    try:
        # 1. Generate an article
        print("Generating article...")
        topic = "The Future of AI in Healthcare"
        article_json = generate_article(topic)
        article = eval(article_json)  # Convert string to dict
        
        # Print the article
        print("\nGenerated Article:")
        print(f"Headline: {article['headline']}")
        print(f"\nIntroduction:\n{article['intro']}")
        print(f"\nBody:\n{article['body']}")
        print(f"\nConclusion:\n{article['conclusion']}")
        
        # 2. Generate audio from the article
        print("\nGenerating audio...")
        
        # Combine article parts
        full_text = f"{article['headline']}. {article['intro']} {article['body']} {article['conclusion']}"
        
        # Create output directory
        output_dir = "generated_audio"
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate audio file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        audio_path = os.path.join(output_dir, f"article_{timestamp}.mp3")
        
        generate_audio(full_text, audio_path)
        print(f"Audio saved to: {audio_path}")
        
        return {
            "article": article,
            "audio_path": audio_path
        }
        
    except Exception as e:
        print(f"Error in pipeline: {str(e)}")
        raise

if __name__ == "__main__":
    main() 