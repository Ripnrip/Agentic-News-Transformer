import streamlit as st
import os
from database_agent import DatabaseAgent
from content_generator import ContentGenerationAgent
from audio_generator import AudioGenerationAgent
from models import NewsArticle, ArticleContent
from datetime import datetime, timedelta
import json
from social_media_agent import SocialMediaAgent
from avatar_generator import AvatarGenerationAgent
from env_validator import validate_conda_env

# Initialize agents
db_agent = DatabaseAgent()
content_agent = ContentGenerationAgent(db_agent)
audio_agent = AudioGenerationAgent()
avatar_agent = AvatarGenerationAgent()
social_agent = SocialMediaAgent()

# Available ElevenLabs voices
VOICES = {
    "Rachel": "21m00Tcm4TlvDq8ikWAM",
    "Domi": "AZnzlk1XvdvUeBnXmlld",
    "Bella": "EXAVITQu4vr4xnSDxMaL",
    "Antoni": "ErXwobaYiN019PkySvjV",
    "Elli": "MF3mGyEYCl7XYWbV9V6O",
    "Josh": "TxGEqnHWrfWFTfGW9XjX",
    "Arnold": "VR6AewLTigWG4xSOukaG",
    "Adam": "pNInz6obpgDQGcFmaJgB",
    "Sam": "yoZ06aMxZJJ28mfd3POQ",
}

def process_raw_text(title: str, text: str, source: str = "manual_input") -> NewsArticle:
    """Process raw text input into a NewsArticle object."""
    return NewsArticle(
        title=title,
        link=f"manual_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        content=ArticleContent(
            text=text,
            html="",  # Raw text input won't have HTML
            markdown=""  # Raw text input won't have markdown
        ),
        source=source,
        source_type="manual",
        published_date=datetime.now()
    )

def main():
    # Validate conda environment
    validate_conda_env()
    
    st.title("AI News Content Generator")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    selected_voice = st.sidebar.selectbox(
        "Select Voice",
        list(VOICES.keys()),
        index=0
    )
    
    # After voice selection in sidebar
    st.sidebar.header("Avatar Options")
    use_avatar = st.sidebar.checkbox("Generate Avatar Video", value=False)
    
    if use_avatar:
        avatar_available = len(avatar_agent.get_available_avatars()) > 0
        if avatar_available:
            enhancement = st.sidebar.checkbox("Enhance Face", value=True)
            resolution = st.sidebar.selectbox(
                "Video Resolution",
                options=["full", "half", "quarter"],
                index=0
            )
        else:
            st.sidebar.warning(
                "Avatar template not found. Add default_avatar.mp4 to the 'avatars' directory."
            )
    
    # Main content area
    st.header("Enter News Content")
    
    # Create tabs for different input methods
    tab1, tab2 = st.tabs(["URL Input", "Raw Text Input"])
    
    articles = []
    
    with tab1:
        # URL input
        urls = st.text_area(
            "Enter URLs (one per line)",
            height=150,
            help="Enter the URLs of news articles you want to process"
        )
        
        if st.button("Process URLs"):
            if urls:
                url_list = [url.strip() for url in urls.split('\n') if url.strip()]
                
                with st.spinner("Processing articles..."):
                    # Create articles from URLs
                    for url in url_list:
                        st.write(f"Processing: {url}")
                        try:
                            # Use NewsSearchAgent to parse article
                            parsed = db_agent._parse_article(url)
                            if parsed and parsed.get('text'):
                                article = NewsArticle(
                                    title=parsed.get('title', 'Untitled'),
                                    link=url,
                                    content=ArticleContent(
                                        text=parsed['text'],
                                        html=parsed.get('html', ''),
                                        markdown=parsed.get('markdown', '')
                                    ),
                                    source="user_input",
                                    source_type="newsapi",
                                    published_date=datetime.now()
                                )
                                articles.append(article)
                                st.success(f"Successfully processed: {url}")
                            else:
                                st.error(f"Could not extract content from: {url}")
                        except Exception as e:
                            st.error(f"Error processing {url}: {str(e)}")
    
    with tab2:
        # Raw text input
        article_title = st.text_input(
            "Article Title",
            help="Enter a title for your article"
        )
        article_text = st.text_area(
            "Article Text",
            height=300,
            help="Enter the raw text of your article"
        )
        article_source = st.text_input(
            "Source (optional)",
            value="Manual Input",
            help="Enter the source of this content"
        )
        
        if st.button("Process Text"):
            if article_title and article_text:
                with st.spinner("Processing text..."):
                    article = process_raw_text(article_title, article_text, article_source)
                    articles.append(article)
                    st.success("Successfully processed text input")
            else:
                st.error("Please provide both a title and text content")

    # Continue with content generation if we have articles
    if articles:
        if st.button("Generate Content", key="generate_content"):
            with st.spinner("Generating content..."):
                # Store articles
                db_agent.store_articles(articles)
                st.success(f"Stored {len(articles)} articles")
                
                # Generate content
                article = content_agent.generate_article("AI Technology News")
                
                # Display generated content
                st.header("Generated Content")
                st.subheader(article['headline'])
                st.write(article['intro'])
                st.write(article['body'])
                st.write(article['conclusion'])
                
                # Generate audio with selected voice
                with st.spinner("Generating audio..."):
                    audio_agent.voice_id = VOICES[selected_voice]
                    audio_content = audio_agent.generate_audio_content(article, content_agent.client)
                    
                    # Display audio and transcripts
                    st.header("Audio Content")
                    st.audio(audio_content['audio_file'])
                    
                    with st.expander("View Script"):
                        st.text(audio_content['script'])
                        
                    with st.expander("View Subtitles"):
                        st.text(open(audio_content['srt_file']).read())
                    
                    # Save results
                    results = {
                        "article": article,
                        "audio": {
                            "file": audio_content['audio_file'],
                            "script": audio_content['script_file'],
                            "srt": audio_content['srt_file'],
                            "voice": selected_voice
                        },
                        "metadata": {
                            "generated_date": datetime.now().isoformat(),
                            "source_urls": [a.link for a in articles]
                        }
                    }
                    
                    # Save to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    output_file = f"generated_content/content_{timestamp}.json"
                    os.makedirs("generated_content", exist_ok=True)
                    with open(output_file, 'w') as f:
                        json.dump(results, f, indent=2)
                        
                    st.download_button(
                        "Download Results",
                        json.dumps(results, indent=2),
                        file_name=f"content_{timestamp}.json",
                        mime="application/json"
                    )

                # After generating audio content
                if 'audio_content' in locals():
                    # Add social media distribution section
                    st.header("Social Media Distribution")
                    
                    # Platform selection
                    platforms = st.multiselect(
                        "Select platforms to publish to",
                        options=list(social_agent.platforms.keys()),
                        default=[]
                    )
                    
                    # Custom personalities
                    st.subheader("Platform Personalities")
                    custom_personalities = {}
                    
                    for platform in platforms:
                        default_personality = social_agent.platform_personalities.get(platform, "default")
                        
                        if platform == "x":
                            options = ["casual", "professional", "enthusiastic"]
                        elif platform == "facebook":
                            options = ["casual", "storyteller", "professional"]
                        elif platform == "linkedin":
                            options = ["thought_leader", "industry_expert", "educator"]
                        else:
                            options = ["default", "casual", "professional"]
                        
                        selected = st.selectbox(
                            f"Personality for {platform}",
                            options=options,
                            index=options.index(default_personality) if default_personality in options else 0
                        )
                        
                        custom_personalities[platform] = selected

if __name__ == "__main__":
    main() 