import streamlit as st
import os
from database_agent import DatabaseAgent
from content_generator import ContentGenerationAgent
from audio_generator import AudioGenerationAgent
from models import NewsArticle, ArticleContent
from datetime import datetime, timedelta
import json
from social_media_agent import SocialMediaAgent

# Initialize agents
db_agent = DatabaseAgent()
content_agent = ContentGenerationAgent(db_agent)
audio_agent = AudioGenerationAgent()
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

def main():
    st.title("AI News Content Generator")
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    selected_voice = st.sidebar.selectbox(
        "Select Voice",
        list(VOICES.keys()),
        index=0
    )
    
    # Main content area
    st.header("Enter News Sources")
    
    # URL input
    urls = st.text_area(
        "Enter URLs (one per line)",
        height=150,
        help="Enter the URLs of news articles you want to process"
    )
    
    if st.button("Generate Content"):
        if urls:
            url_list = [url.strip() for url in urls.split('\n') if url.strip()]
            
            with st.spinner("Processing articles..."):
                # Create articles from URLs
                articles = []
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
                
                if articles:
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
                                "source_urls": url_list
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
                
                # Schedule posting
                schedule = st.checkbox("Schedule for later")
                post_time = None
                
                if schedule:
                    post_time = st.date_input("Post date") 
                    post_hour = st.slider("Hour", 0, 23, 9)
                    post_minute = st.slider("Minute", 0, 59, 0, step=5)
                    post_time = datetime.combine(post_time, datetime.min.time()) + timedelta(hours=post_hour, minutes=post_minute)
                    
                    st.write(f"Scheduled for: {post_time.strftime('%Y-%m-%d %H:%M')}")
                
                # Post button
                if st.button("Post to Social Media"):
                    with st.spinner("Posting to social media..."):
                        # Prepare media files
                        media_files = {
                            platform: [audio_content["audio_file"]] for platform in platforms
                        }
                        
                        # Post or schedule
                        if schedule and post_time:
                            results = social_agent.schedule_post(
                                content=article,
                                media_files=media_files,
                                platforms=platforms,
                                custom_personalities=custom_personalities,
                                post_time=post_time
                            )
                            
                            if results.get("scheduled"):
                                st.success(f"Scheduled posts for {post_time.strftime('%Y-%m-%d %H:%M')}")
                            else:
                                st.error("Failed to schedule posts")
                        else:
                            results = social_agent.post_to_platforms(
                                content=article,
                                media_files=media_files,
                                platforms=platforms,
                                custom_personalities=custom_personalities
                            )
                            
                            # Display results
                            for platform, result in results.items():
                                if result.get("success"):
                                    st.success(f"Posted to {platform}! Post ID: {result.get('post_id')}")
                                else:
                                    st.error(f"Failed to post to {platform}: {result.get('error')}")
        else:
            st.error("Please enter at least one URL")

if __name__ == "__main__":
    main() 