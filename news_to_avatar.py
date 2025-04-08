"""News to Avatar Pipeline - Convert news articles to lip-synced avatar videos."""
import os
import streamlit as st
import urllib.parse
import subprocess
import sys
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
import time
import boto3
from botocore.exceptions import ClientError
import requests
import uuid
import traceback

# Set page config at the very beginning
st.set_page_config(
    page_title="News to Avatar",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

from agents import NewsSearchAgent
from content_generator import ContentGenerationAgent, ArticleRequest, SimilarArticle
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent, VideoSettings, VideoResult
from database_agent import DatabaseAgent
import json
from env_validator import validate_conda_env

# After imports but before functions, add the avatar map
# Define avatar mapping for Sync.so
SYNC_AVATARS = [
    {
        "id": "b2a8c48e",
        "name": "Sexy News Anchor", 
        "description": "A charismatic news anchor who delivers content with style and charm.",
        "image_url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3.png",
        "video_url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4"
    }
]

# Create a lookup map for easy access
SYNC_AVATAR_MAP = {avatar["id"]: avatar["video_url"] for avatar in SYNC_AVATARS}

def launch_main_app():
    """Switch to content generator mode within the same app"""
    # Set app mode to content generator
    st.session_state.app_mode = "content_generator"
    # Force a rerun to apply the change
    st.experimental_rerun()

# Initialize session state for tab selection and caching
if "tab_selection" not in st.session_state:
    st.session_state.tab_selection = 0  # Default to News tab
    
if "switch_to_tab" not in st.session_state:
    st.session_state.switch_to_tab = None
    
if "process_article_with_url" not in st.session_state:
    st.session_state.process_article_with_url = None
    
if "processed_urls" not in st.session_state:
    st.session_state.processed_urls = {}

# Initialize audio session state variables if not present
if "generated_audio" not in st.session_state:
    st.session_state.generated_audio = None
    
if "generated_audio_url" not in st.session_state:
    st.session_state.generated_audio_url = None
    
if "article_title" not in st.session_state:
    st.session_state.article_title = None

if "article_content" not in st.session_state:
    st.session_state.article_content = None
    
if "article_keywords" not in st.session_state:
    st.session_state.article_keywords = []

if "job_id" not in st.session_state:
    st.session_state.job_id = None
    
if "job_status" not in st.session_state:
    st.session_state.job_status = None
    
if "video_result" not in st.session_state:
    st.session_state.video_result = None

# Initialize agents
def init_agents():
    """Initialize all agents needed for the news-to-avatar pipeline."""
    print("Initializing agents for news-to-avatar pipeline...")
    
    # News agent for fetching and parsing articles
    news_agent = NewsSearchAgent()
    
    # Content generation agent for creating scripts
    db_agent = DatabaseAgent()
    content_agent = ContentGenerationAgent(db_agent=db_agent)
    
    # Audio agent for text-to-speech
    audio_agent = AudioGenerationAgent()
    
    # Avatar agent for generating videos
    avatar_agent = AvatarGenerationAgent()
    
    return news_agent, content_agent, audio_agent, avatar_agent

def process_article_url(url, news_agent):
    """Process a news article from a URL."""
    try:
        # Reset the processing state when a new article URL is submitted
        if 'parsing_article' in st.session_state:
            print(f"🔄 Clearing previous parsing state: {st.session_state.parsing_article}")
            del st.session_state.parsing_article
        
        # Set a flag to indicate we're parsing an article
        st.session_state.parsing_article = url
        st.session_state.parsing_started_at = datetime.now()
        
        print(f"🔍 Starting article parsing at {st.session_state.parsing_started_at.strftime('%H:%M:%S')}: {url}")
        st.write(f"🔍 Parsing article from: {url}")
        
        # Create a timestamp for progress tracking
        start_time = time.time()
        
        @dataclass
        class Article:
            title: str = "User Provided Article"
            link: str = url
            source: str = "User Input"
            published_date: datetime = datetime.now()
            source_type: str = "web"
            author: str = "Unknown"
            engagement: dict = None
        
        # Parse the article using the news agent
        # This is an async function, so we need to use asyncio
        parsing_progress = st.empty()
        parsing_progress.info("Starting article parser...")
        parsed = asyncio.run(news_agent.parse_article(url))
        
        # Calculate parsing time
        parsing_time = time.time() - start_time
        print(f"⏱️ Article parsing completed in {parsing_time:.2f} seconds")
        
        # Clear the parsing flag when done
        if 'parsing_article' in st.session_state:
            print(f"✅ Clearing parsing flag after successful parsing")
            del st.session_state.parsing_article
        
        # Check if parsing was successful
        if parsed:
            # Check if we have content in different formats
            if parsed.get("text"):
                # Get content stats
                content_text = parsed.get("text")
                word_count = len(content_text.split())
                char_count = len(content_text)
                
                # Log content statistics
                print(f"📊 Article stats: {char_count} chars, {word_count} words")
                parsing_progress.success(f"✅ Successfully parsed: {word_count} words, {char_count} chars")
                
                # Verify if content is not too long
                if word_count > 3000:
                    st.warning(f"⚠️ Article is very long ({word_count} words). Processing may take longer.")
                
                return {
                    "title": parsed.get("title", "Untitled Article"),
                    "text": content_text,
                    "html": parsed.get("html", ""),
                    "markdown": parsed.get("markdown", ""),
                    "url": url,
                    "word_count": word_count,
                    "parsing_time": parsing_time
                }
            else:
                error_msg = f"❌ Could not extract text content from: {url}"
                print(error_msg)
                parsing_progress.error(error_msg)
                
                # Clear the parsing flag on error
                if 'parsing_article' in st.session_state:
                    del st.session_state.parsing_article
                return None
        else:
            error_msg = f"❌ Failed to parse article from: {url}"
            print(error_msg)
            parsing_progress.error(error_msg)
            
            # Clear the parsing flag on error
            if 'parsing_article' in st.session_state:
                del st.session_state.parsing_article
            return None
    except Exception as e:
        # Log the exception
        error_msg = f"❌ Error processing {url}: {str(e)}"
        print(error_msg)
        import traceback
        print(f"📋 Traceback: {traceback.format_exc()}")
        st.error(error_msg)
        
        # Clear the parsing flag on error
        if 'parsing_article' in st.session_state:
            del st.session_state.parsing_article
        return None

def generate_script(article_content, content_agent):
    """Generate a 30-second script from article content."""
    try:
        st.write("Generating script from article...")
        
        # Create article request
        request = ArticleRequest(
            topic=article_content,  # Use full content
            tone="news",
            length="short"
        )
        
        # Generate script using content agent
        result = content_agent.generate_article_content(request)
        
        if result:
            st.success("Script generated successfully!")
            return result
        else:
            st.error("Failed to generate script: No content in result")
            return None
    except Exception as e:
        st.error(f"Error generating script: {str(e)}")
        return None

def generate_audio(script, audio_agent):
    """Generate audio from script using ElevenLabs."""
    try:
        st.write("Generating audio from script...")
        
        # Import AudioRequest explicitly to ensure it's available
        from audio_generator import AudioRequest
        
        # Create audio request
        request = AudioRequest(
            text=script,
            title="News Script",
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Default voice ID
            output_dir="generated_audio",
            upload_to_s3=True,  # Enable S3 upload
            s3_bucket="vectorverseevolve",
            s3_region="us-west-2"
        )
        
        # Generate audio
        result = audio_agent.generate_audio_content(request)
        
        if result and hasattr(result, 'audio_file'):
            if result.audio_url:
                st.success(f"Audio generated and uploaded successfully! URL: {result.audio_url}")
            else:
                st.success("Audio generated successfully! (Not uploaded to S3)")
            
            # Return both the local file path and the S3 URL
            return {
                'audio_file': result.audio_file,
                'audio_url': result.audio_url
            }
        else:
            st.error("Failed to generate audio: No audio file in result")
            return None
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return None

def generate_avatar_video(audio_url, avatar_id=None, poll_for_completion=True, poll_interval=15, max_attempts=20):
    """Generate avatar video from audio.
    
    Args:
        audio_url: URL to the audio file
        avatar_id: Optional avatar ID to use
        poll_for_completion: Whether to wait for job completion
        poll_interval: How often to check job status (seconds)
        max_attempts: Maximum number of polling attempts
        
    Returns:
        Video result object
    """
    try:
        # Get video URL from avatar ID or use default
        video_url = SYNC_AVATAR_MAP.get(avatar_id) if avatar_id else SYNC_AVATARS[0]['video_url']
        
        # Generate video with polling parameters
        video_result = avatar_agent.generate_video(
            audio_url=audio_url,
            video_url=video_url,
            poll_for_completion=poll_for_completion,
            poll_interval=poll_interval,
            max_attempts=max_attempts
        )
        
        return video_result
    except Exception as e:
        st.error(f"Error generating video: {str(e)}")
        return None

# Function to handle rerunning the app based on streamlit version
def streamlit_rerun():
    """Helper function to rerun the app, handling different streamlit versions"""
    try:
        # Try the standard rerun() method
        import streamlit as st
        st.rerun()
    except (AttributeError, Exception) as e:
        try:
            # Try experimental_rerun() as fallback
            st.experimental_rerun()
        except (AttributeError, Exception):
            # Final fallback - use JavaScript to force refresh
            st.write("""
            <script>
            // Refresh the page to apply changes
            window.location.reload();
            </script>
            """, unsafe_allow_html=True)
            st.warning("Auto-refresh not supported in this Streamlit version. Please refresh the page manually.")

def reset_session_state():
    """Reset the session state variables after job completion."""
    print("🔄 Resetting news_to_avatar.py session state...")
    
    # Record time of reset
    reset_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏱️ Reset triggered at: {reset_time}")
    
    # Don't reset everything - just the processing state
    processing_keys = [
        "process_article_with_url", 
        "processed_urls", 
        "job_id", 
        "job_status", 
        "video_result", 
        "sync_job_cache", 
        "parsing_article", 
        "parsing_started_at",
        "processing_url", 
        "needs_reset",
        "reset_after_completion"
    ]
    
    # Count how many keys were actually cleared
    cleared_count = 0
    
    for key in processing_keys:
        if key in st.session_state:
            try:
                # Try to log the value before clearing (for debugging)
                value_summary = str(st.session_state[key])
                if len(value_summary) > 100:
                    value_summary = value_summary[:100] + "..."
                print(f"🔄 Clearing session state: {key} = {value_summary}")
            except:
                print(f"🔄 Clearing session state: {key} (value cannot be displayed)")
                
            del st.session_state[key]
            cleared_count += 1
    
    # Keep audio files and results if needed for reuse
    
    # Flag to indicate reset was done
    st.session_state.state_reset_done = True
    print(f"✅ Session state has been reset. Cleared {cleared_count} keys.")
    
    # This is a safer way to reload the page in Streamlit
    print("🔄 Triggering page reload via st.experimental_rerun()")
    try:
        st.experimental_rerun()
    except Exception as e:
        print(f"⚠️ Error during page reload: {str(e)}")
        # Fall back to a regular rerun if experimental_rerun fails
        pass

def post_video_to_x(video_url, text, hashtags=None):
    """Post the video to X (Twitter).
    
    Args:
        video_url: URL to the video file
        text: Text content for the post
        hashtags: Optional list of hashtags to include
        
    Returns:
        Tuple of (success, message)
    """
    try:
        from social_media_agent import SocialMediaAgent
        
        # Initialize the social media agent
        agent = SocialMediaAgent()
        
        # Check if X platform is available
        if not agent._check_platform_available("x"):
            return False, "X platform is not configured. Check your environment variables."
        
        # Post the video to X
        result = agent.post_video_to_x(text, video_url, hashtags)
        
        if result.success:
            return True, f"Successfully posted to X! {result.post_url}"
        else:
            error_message = result.message
            
            # Check if this is a permission error
            if "Permission error" in error_message or "403" in error_message:
                return False, f"X API permission error: Your API key doesn't have sufficient access level. Please check the X API documentation for upgrading your access level."
            
            return False, f"Failed to post to X: {error_message}"
            
    except Exception as e:
        return False, f"Error posting to X: {str(e)}"

def main():
    """Run the app."""
    # Validate conda environment first
    validate_conda_env(skip=os.environ.get("SKIP_CONDA_CHECK") == "true")
    
    # Initialize app mode if not already set
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "news_to_avatar"
        
    # Add app mode selector in sidebar
    with st.sidebar:
        st.title("🧭 Navigation")
        
        # Remove the problematic CSS section and just use buttons
        st.markdown("""
        <div style="background-color:#f0f2f6; padding:10px; border-radius:10px; margin-bottom:10px;">
            <p style="font-weight:bold; margin-bottom:8px;">Select App Mode:</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Actual mode selector with buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🎬 News to Avatar", use_container_width=True, 
                         disabled=st.session_state.app_mode == "news_to_avatar",
                         type="primary" if st.session_state.app_mode == "news_to_avatar" else "secondary"):
                st.session_state.app_mode = "news_to_avatar"
                st.experimental_rerun()
        
        with col2:
            if st.button("📝 Content Generator", use_container_width=True,
                         disabled=st.session_state.app_mode == "content_generator",
                         type="primary" if st.session_state.app_mode == "content_generator" else "secondary"):
                st.session_state.app_mode = "content_generator"
                st.experimental_rerun()
        
        # Add Reset button in sidebar
        st.sidebar.title("🛠️ Tools")
        if st.sidebar.button("🔄 Reset App State", help="Use this if the app gets stuck"):
            print("🔄 Manual reset button pressed")
            reset_session_state()
    
    # Check if we need to reset state from a previous job
    if "needs_reset" in st.session_state and st.session_state.needs_reset:
        print("🔄 Session state needs reset flag detected")
        st.session_state.needs_reset = False
        reset_session_state()
    
    # Check for stalled parsing - if parsing_article is set for more than 2 minutes, reset it
    if "parsing_article" in st.session_state and "parsing_started_at" not in st.session_state:
        print("⚠️ Found parsing_article without timestamp - adding timestamp now")
        st.session_state.parsing_started_at = datetime.now()
    elif "parsing_article" in st.session_state and "parsing_started_at" in st.session_state:
        # Check if parsing has been ongoing for too long (more than 2 minutes)
        elapsed_seconds = (datetime.now() - st.session_state.parsing_started_at).total_seconds()
        
        print(f"⏱️ Article parsing in progress for {elapsed_seconds:.1f} seconds: {st.session_state.parsing_article}")
        
        if elapsed_seconds > 120:
            print(f"🛑 Article parsing has been stuck for {elapsed_seconds:.1f} seconds - resetting state")
            st.warning(f"⚠️ Article parsing has been running for too long ({int(elapsed_seconds)} seconds). Resetting state...")
            reset_session_state()
    elif "parsing_started_at" in st.session_state and "parsing_article" not in st.session_state:
        # Clean up the timestamp if parsing is done
        print("🧹 Cleaning up parsing timestamp - parsing is finished")
        del st.session_state.parsing_started_at
    
    # Also check job status for completion
    if "job_status" in st.session_state and st.session_state.job_status == "COMPLETED":
        print("✅ Job completed - setting needs_reset flag for next reload")
        # Set a flag to reset on next reload - this is less disruptive than an immediate reset
        st.session_state.needs_reset = True
        st.session_state.reset_after_completion = True
    
    # Initialize common agents
    # We need to initialize these globally since they're used in both modes
    global db_agent, content_agent, audio_agent, avatar_agent, social_agent, news_agent
    if 'agents_initialized' not in st.session_state:
        print("Initializing agents for both modes...")
        news_agent = NewsSearchAgent()
        db_agent = DatabaseAgent()
        content_agent = ContentGenerationAgent(db_agent)
        audio_agent = AudioGenerationAgent()
        avatar_agent = AvatarGenerationAgent()
        social_agent = SocialMediaAgent()
        st.session_state.agents_initialized = True
    
    # Switch between apps based on mode
    if st.session_state.app_mode == "news_to_avatar":
        # News to Avatar mode
        show_news_to_avatar()
    else:
        # Content Generator mode
        show_content_generator_mode()

def show_news_to_avatar():
    """Show the News to Avatar interface"""
    # Set page title and description
    st.title("News to Avatar Video Generator")
    st.markdown("""
        <div style="background-color:#f0f2f6; padding:10px; border-radius:10px; margin-bottom:10px;">
            <p style="margin:0; padding:5px;">Convert news articles to lip-synced avatar videos with AI ✨</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Add clear app identification banner
    st.markdown(
        """
        <div style="background-color:#FF5C5C; padding:10px; border-radius:10px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center;">📱 NEWS TO AVATAR</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Add tab selection for different stages
    if "tab_selection" not in st.session_state:
        st.session_state.tab_selection = 0
    
    # Check if we need to switch tabs
    if "switch_to_tab" in st.session_state:
        st.session_state.tab_selection = st.session_state.switch_to_tab
        del st.session_state.switch_to_tab
    
    news_tab, generate_tab, jobs_tab, share_tab = st.tabs(["📰 News", "📺 Generate", "🔄 Jobs", "📱 Share"])
    
    with news_tab:
        if st.session_state.tab_selection == 0:
            display_news_tab(news_agent, content_agent, audio_agent)
            
    with generate_tab:
        if st.session_state.tab_selection == 1:
            display_generate_tab(avatar_agent)
            
    with jobs_tab:
        if st.session_state.tab_selection == 2:
            display_jobs_tab(avatar_agent)
    
    with share_tab:
        if st.session_state.tab_selection == 3:
            display_share_tab()

def show_content_generator_mode():
    """Show the Content Generator interface"""
    # Import from app.py - specifically the process_articles function
    # which will be used for the content generator mode
    from app import process_articles as app_process_articles
    
    # Set page title
    st.title("AI News Content Generator")
    
    # Add clear app identification banner
    st.markdown(
        """
        <div style="background-color:#0068c9; padding:10px; border-radius:10px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center;">📝 CONTENT GENERATOR</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Sidebar for configuration
    st.sidebar.header("Configuration")
    selected_voice = st.sidebar.selectbox(
        "Select Voice",
        list(VOICES.keys()),
        index=0,
        key="voice_selector_main"
    )
    
    # Set avatar generation to always be on - no toggle needed
    use_avatar = True
    
    # Main content area
    st.header("Enter News Content")
    
    # Create tabs for different input methods
    input_tab, paste_tab = st.tabs(["Enter URLs", "Paste Article Text"])

    with input_tab:
        # URL input with prefilled IBM article
        urls = st.text_area(
            "Enter URLs (one per line)",
            height=150,
            value="https://techcrunch.com/2025/04/07/ibm-acquires-consultancy-hakkoda-as-it-continues-its-ai-investment-push/",
            help="Enter the URLs of news articles you want to process",
            key="url_input_main_tab"
        )
        
        url_button = st.button("Generate from URLs", key="generate_url_button_main")

    with paste_tab:
        # Direct text input
        article_title = st.text_input("Article Title", help="Enter the title of the article", key="article_title_input_paste")
        article_source = st.text_input("Article Source (optional)", help="Enter the source of the article", key="article_source_input_paste")
        article_text = st.text_area(
            "Paste Article Text",
            height=300,
            help="Paste the full text of the article",
            key="article_text_input_paste"
        )
        
        text_button = st.button("Generate from Text", key="generate_text_button_paste")

    # Process article from URLs
    if url_button and urls:
        url_list = [url.strip() for url in urls.split('\n') if url.strip()]
        
        with st.spinner("Processing articles..."):
            # Create articles from URLs
            articles = []
            for url in url_list:
                st.write(f"Processing: {url}")
                try:
                    # Use NewsSearchAgent to parse article
                    parsed = asyncio.run(news_agent.parse_article(url))
                    if parsed and parsed.get('text'):
                        # Ensure all fields have valid values, replacing None with empty strings
                        title = parsed.get('title', 'Untitled')
                        article_text = parsed.get('text', '')
                        html_content = parsed.get('html', '')
                        markdown_content = parsed.get('markdown', '')
                        
                        # Create the article with validated fields
                        article = NewsArticle(
                            title=title,
                            link=url,
                            content=ArticleContent(
                                text=article_text,
                                html=html_content,
                                markdown=markdown_content
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
            
            # Process the articles using our process_articles function
            # Since we've already initialized the agents globally, we have access to them
            if articles:
                app_process_articles(articles, selected_voice, use_avatar)

    # Process article from pasted text
    elif text_button and article_text:
        if not article_title:
            st.error("Please enter an article title")
        else:
            with st.spinner("Processing pasted article..."):
                # Create article from pasted text
                article = NewsArticle(
                    title=article_title,
                    link="",  # No URL for pasted content
                    content=ArticleContent(
                        text=article_text,
                        html="",  # No HTML for pasted content
                        markdown=""  # No markdown for pasted content
                    ),
                    source=article_source if article_source else "manual_input",
                    source_type="user_paste",
                    published_date=datetime.now()
                )
                
                # Process the article using the process_articles function
                app_process_articles([article], selected_voice, use_avatar)

def display_news_tab(news_agent, content_agent, audio_agent):
    """Display the news tab with article input and processing."""
    st.header("📰 News Article Input")
    
    # Create a more user-friendly interface
    st.markdown("""
    <div style="background-color:#f8f9fa; padding:10px; border-radius:10px; margin-bottom:15px;">
        <p>Enter a URL to any news article, and we'll convert it to an avatar video!</p>
        <p>The system will:</p>
        <ol>
            <li>Parse the article content</li>
            <li>Generate a script</li>
            <li>Create audio narration</li>
            <li>Produce a lip-synced avatar video</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)
    
    # Add some example URLs
    with st.expander("📋 Example URLs (click to use)"):
        example_urls = [
            "https://techcrunch.com/2025/04/07/ibm-acquires-consultancy-hakkoda-as-it-continues-its-ai-investment-push/",
            "https://techcrunch.com/2025/04/07/googles-ai-mode-now-lets-users-ask-complex-questions-about-images/",
            "https://www.theverge.com/2025/4/7/24121574/openai-next-frontier-humanoid-robots"
        ]
        
        for i, url in enumerate(example_urls):
            if st.button(f"Use Example {i+1}", key=f"example_url_{i}"):
                st.session_state.url_input = url
                st.experimental_rerun()
    
    # News input section with a default value if set in session state
    default_url = st.session_state.get("url_input", "https://techcrunch.com/2025/04/07/ibm-acquires-consultancy-hakkoda-as-it-continues-its-ai-investment-push/")
    
    url_input = st.text_input(
        "Enter article URL:",
        value=default_url,
        help="Enter a URL to a news article to process",
        key="url_input"
    )
    
    col1, col2 = st.columns([1, 3])
    with col1:
        process_button = st.button("🔍 Parse Article", use_container_width=True)
    with col2:
        st.markdown("<div style='height: 38px;'></div>", unsafe_allow_html=True)
        
    if process_button:
        if not url_input or not url_input.startswith(("http://", "https://")):
            st.error("Please enter a valid URL starting with http:// or https://")
        else:
            with st.spinner("Processing article..."):
                content = process_article_url(url_input, news_agent)
                if content:
                    script_result = generate_script(content, content_agent)
                    if script_result:
                        # Access script_result as a dictionary
                        audio_result = generate_audio(script_result['content'], audio_agent)
                        if audio_result:
                            st.session_state.generated_audio = audio_result['audio_file']
                            st.session_state.generated_audio_url = audio_result['audio_url']
                            st.session_state.generated_title = script_result['article']['headline']
                            st.success("✅ Article processed successfully! Switch to Generate tab to create video.")
                            
                            # Display the generated script
                            with st.expander("📝 View Generated Script"):
                                st.markdown(f"## {script_result['article']['headline']}")
                                st.write(script_result['article']['intro'])
                                st.write(script_result['article']['body'])
                                st.write(script_result['article']['conclusion'])
                            
                            # Display the audio
                            if st.session_state.generated_audio:
                                st.subheader("🔊 Generated Audio")
                                st.audio(st.session_state.generated_audio)
                            
                            # Auto-switch to Generate tab
                            st.session_state.tab_selection = 1

def display_generate_tab(avatar_agent):
    """Display the generate tab with avatar selection and video generation."""
    st.header("📺 Avatar Video Generation")
    
    # Check if audio is available
    if "generated_audio_url" in st.session_state and st.session_state.generated_audio_url:
        # Avatar selection and video generation
        st.subheader("👤 Avatar Selection")
        
        # Display available avatars
        for avatar in SYNC_AVATARS:
            st.write(f"**{avatar['name']}**")
            if avatar['image_url']:
                st.image(avatar['image_url'], width=150)
            st.write(avatar['description'])
        
        # Generate video button
        if st.button("🎬 Generate Video"):
            with st.spinner("Generating avatar video..."):
                video_result = generate_avatar_video(
                    audio_url=st.session_state.generated_audio_url,
                    avatar_id=SYNC_AVATARS[0]['id'],  # Using first avatar by default
                    poll_for_completion=True,
                    poll_interval=15,
                    max_attempts=20
                )
                
                if video_result and hasattr(video_result, "video_url") and video_result.video_url:
                    st.session_state.video_result = video_result
                    st.session_state.job_id = video_result.job_id
                    st.session_state.job_status = video_result.status
                    
                    st.success("✅ Video generated successfully!")
                    st.video(video_result.video_url)
                    
                    # Auto-switch to Share tab
                    st.session_state.tab_selection = 3
                elif hasattr(video_result, "status") and video_result.status in ["PENDING", "PROCESSING"]:
                    st.session_state.video_result = video_result
                    st.session_state.job_id = video_result.job_id
                    st.session_state.job_status = video_result.status
                    
                    st.info(f"🔄 Video generation started with job ID: {video_result.job_id}")
                    st.info("The job is processing. Check the Jobs tab for status updates.")
                    
                    # Auto-switch to Jobs tab
                    st.session_state.tab_selection = 2
                else:
                    st.error("❌ Video generation failed. Please try again.")
    else:
        st.warning("⚠️ Please generate audio content in the News tab first.")
        st.button("Go to News Tab", on_click=lambda: setattr(st.session_state, "tab_selection", 0))

def display_jobs_tab(avatar_agent):
    """Display the jobs tab with job status and management."""
    st.header("🔄 Job Management")
    
    # Current job status
    if "job_id" in st.session_state and st.session_state.job_id:
        st.subheader("Current Job")
        
        job_id = st.session_state.job_id
        
        # Check status button
        if st.button("🔄 Refresh Job Status"):
            with st.spinner("Checking job status..."):
                job_status = avatar_agent.check_job_status(job_id)
                
                # Update session state
                status = job_status.get("status", "UNKNOWN")
                st.session_state.job_status = status
                
                if status == "COMPLETED" and job_status.get("outputUrl"):
                    # Create a VideoResult object to store in session state
                    from dataclasses import dataclass
                    
                    @dataclass
                    class VideoResult:
                        job_id: str
                        status: str
                        video_url: str
                        error: str = None
                    
                    st.session_state.video_result = VideoResult(
                        job_id=job_id,
                        status=status,
                        video_url=job_status.get("outputUrl")
                    )
                    
                    st.success(f"✅ Job completed! Video URL: {job_status.get('outputUrl')}")
                    st.video(job_status.get("outputUrl"))
                    
                    # Auto-switch to Share tab
                    st.session_state.tab_selection = 3
                elif status == "FAILED" or status == "REJECTED":
                    st.error(f"❌ Job failed: {job_status.get('error', 'Unknown error')}")
                else:
                    st.info(f"⏳ Job status: {status}")
        
        # Display current status
        st.write(f"Job ID: {job_id}")
        st.write(f"Status: {st.session_state.job_status}")
    
    # List of recent jobs
    st.subheader("Recent Jobs")
    jobs = avatar_agent.list_saved_jobs()
    
    if jobs:
        # Sort jobs by creation date, newest first
        jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        for job in jobs[:5]:  # Show only the 5 most recent jobs
            with st.expander(f"Job: {job['id']} - Status: {job['status']}"):
                st.write(f"Created: {job.get('created_at', 'Unknown')}")
                st.write(f"Last checked: {job.get('last_checked', 'Unknown')}")
                
                if job['status'] == "COMPLETED" and job.get('data', {}).get('outputUrl'):
                    video_url = job['data']['outputUrl']
                    st.video(video_url)
                    
                    # Button to use this video
                    if st.button(f"Use this video (Job: {job['id'][:8]}...)"):
                        # Create a VideoResult object to store in session state
                        from dataclasses import dataclass
                        
                        @dataclass
                        class VideoResult:
                            job_id: str
                            status: str
                            video_url: str
                            error: str = None
                        
                        st.session_state.video_result = VideoResult(
                            job_id=job['id'],
                            status=job['status'],
                            video_url=video_url
                        )
                        
                        # Auto-switch to Share tab
                        st.session_state.tab_selection = 3
                        streamlit_rerun()
    else:
        st.info("No jobs found. Generate some videos first!")

def display_share_tab():
    """Display the share tab with social media sharing options."""
    st.header("📱 Share Your Content")
    
    # Check if we have a video to share
    if "video_result" in st.session_state and st.session_state.video_result:
        video_result = st.session_state.video_result
        
        # Display the video
        if hasattr(video_result, "video_url") and video_result.video_url:
            st.video(video_result.video_url)
            
            # Get video metadata for sharing
            video_url = video_result.video_url
            
            # Try to get the title from session state or use a default
            if "generated_title" in st.session_state:
                video_title = st.session_state.generated_title
            else:
                video_title = "AI-Generated News Video"
            
            # Hashtag options
            st.subheader("Customize Your Post")
            
            # Let user edit title for the social post
            share_title = st.text_input("Post Text:", 
                                        value=f"🎬 {video_title}", 
                                        max_chars=200,
                                        help="Enter the text to accompany your video post")
            
            # Hashtag options
            default_hashtags = ["AI", "NewsAnchor", "AIVideo", "TechNews"]
            hashtags = st.text_input("Hashtags (comma separated):", 
                                     value=", ".join(default_hashtags),
                                     help="Enter hashtags separated by commas")
            
            # Parse the hashtags
            if hashtags:
                hashtag_list = [tag.strip().replace('#', '') for tag in hashtags.split(',')]
            else:
                hashtag_list = []
            
            # Preview the post
            st.subheader("Post Preview")
            preview_text = share_title
            if hashtag_list:
                hashtag_preview = ' '.join([f"#{tag}" for tag in hashtag_list])
                preview_text = f"{preview_text} {hashtag_preview}"
            
            st.info(f"{preview_text}\n\n[Video will be attached]")
            
            # X API access level information
            with st.expander("ℹ️ About X API Access Levels"):
                st.markdown("""
                **Important Note on X (Twitter) API Access:**
                
                The X API has different access levels and permissions:
                - **Basic**: Limited access to post tweets
                - **Elevated**: Full access to post tweets and media
                - **Pro/Enterprise**: Complete API access
                
                If you encounter issues posting to X, you may need to upgrade your API access level:
                1. Visit [X Developer Portal](https://developer.x.com/en/portal/dashboard)
                2. Click on your project/app
                3. Go to "User authentication settings"
                4. Make sure "Read and write" permissions are enabled
                5. Under "App permissions", select "Read and Write"
                6. You may need to apply for Elevated access if you're on Basic access
                
                Learn more at [X Developer Documentation](https://developer.x.com/en/docs)
                """)
            
            # Add a button to post to X
            if st.button("🐦 Post to X", help="Share this video on X (Twitter)"):
                with st.spinner("Posting to X..."):
                    # Call the function to post to X
                    result = post_video_to_x(
                        video_url=video_url,
                        text=share_title,
                        hashtags=hashtag_list
                    )
                    
                    # Display the result
                    if result[0]:
                        st.success(f"✅ Successfully posted to X! {result[1]}")
                    else:
                        st.error(f"❌ Failed to post to X: {result[1]}")
                            
                # Provide alternative manual sharing option
                st.write("---")
                st.subheader("Manual Sharing Option")
                st.write("If automatic sharing isn't working, you can copy the post text and video URL to share manually:")
                
                # Create copyable text fields
                st.text_area("Post Text (Copy this)", value=preview_text, height=100)
                st.text_input("Video URL (Copy this)", value=video_url)
                
                # Link to open X compose window directly
                encoded_text = preview_text.replace(" ", "%20").replace("#", "%23").replace("\n", "%0A")
                x_compose_url = f"https://x.com/intent/tweet?text={encoded_text}"
                st.markdown(f"[📝 Open X Compose Window]({x_compose_url})")
        else:
            st.warning("No video URL found. Generate a video first before sharing.")
    else:
        st.info("No video has been generated yet. Go to the News tab to process an article and generate a video.")
        st.button("Go to News Tab", on_click=lambda: setattr(st.session_state, "switch_to_tab", 0))

# Add S3 upload helper function
def upload_file_to_s3(file_path, s3_key=None):
    """Upload a file to S3 and return the public URL.
    
    Args:
        file_path: Path to the file to upload
        s3_key: Optional key to use for the file in S3
        
    Returns:
        The public URL of the uploaded file, or None if upload fails
    """
    try:
        # Get S3 credentials from environment variables
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        bucket_name = "vectorverseevolve"
        region = "us-west-2"
        
        if not aws_access_key or not aws_secret_key:
            st.error("❌ AWS credentials not found in environment variables")
            return None
            
        # Create S3 client
        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key
        )
        
        # If no key provided, use the filename
        if not s3_key:
            s3_key = os.path.basename(file_path)
            
        # Clean up key for S3 (replace spaces with underscores)
        s3_key = s3_key.replace(' ', '_')
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'  # Default
        if file_path.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif file_path.lower().endswith('.wav'):
            content_type = 'audio/wav'
        elif file_path.lower().endswith('.mp4'):
            content_type = 'video/mp4'
            
        # Set extra args for upload
        extra_args = {
            'ContentType': content_type,
            'ACL': 'public-read'  # Make file publicly accessible
        }
        
        # Upload the file
        s3_client.upload_file(
            file_path,
            bucket_name,
            s3_key,
            ExtraArgs=extra_args
        )
        
        # Generate the public URL
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        return s3_url
        
    except Exception as e:
        st.error(f"❌ Error uploading to S3: {str(e)}")
        return None

if __name__ == "__main__":
    main() 