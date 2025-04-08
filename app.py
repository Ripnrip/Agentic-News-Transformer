import streamlit as st
import os
from database_agent import DatabaseAgent, SearchQuery
from content_generator import ContentGenerationAgent, SimilarArticle
from audio_generator import AudioGenerationAgent, AudioRequest
from models import NewsArticle, ArticleContent
from datetime import datetime, timedelta
import json
from social_media_agent import SocialMediaAgent
from avatar_generator import AvatarGenerationAgent
from env_validator import validate_conda_env
from agents import NewsSearchAgent
import asyncio
import requests
import subprocess
import sys
import time
import traceback
import math

# Helper function to reset session state
def reset_session_state():
    """Reset the session state variables after job completion."""
    print("🔄 Resetting app.py session state...")
    
    # Record time of reset
    reset_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"⏱️ Reset triggered at: {reset_time}")
    
    # Don't reset everything - just the processing state
    processing_keys = [
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

# Initialize agents
db_agent = DatabaseAgent()
content_agent = ContentGenerationAgent(db_agent)
audio_agent = AudioGenerationAgent()
avatar_agent = AvatarGenerationAgent()
social_agent = SocialMediaAgent()
news_agent = NewsSearchAgent()

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

# Helper functions for news to avatar processing
def process_article_url(url, news_agent):
    """Process a single article URL and return its content."""
    # Reset state if already parsing
    if "parsing_article" in st.session_state:
        print(f"🔄 Clearing previous parsing state: {st.session_state.parsing_article}")
        del st.session_state.parsing_article
        
    # Set flag that we're parsing an article
    st.session_state.parsing_article = True
    st.session_state.processing_url = url
    st.session_state.parsing_started_at = datetime.now()
    
    print(f"🔍 Starting article parsing at {st.session_state.parsing_started_at.strftime('%H:%M:%S')}: {url}")
    
    # Create a timestamp for progress tracking
    start_time = time.time()
    
    # Create a placeholder for status updates
    parsing_progress = st.empty()
    parsing_progress.info(f"🔍 Parsing article from: {url}")
    
    try:
        # Use NewsSearchAgent to parse article
        parsed = asyncio.run(news_agent.parse_article(url))
        
        # Calculate parsing time
        parsing_time = time.time() - start_time
        print(f"⏱️ Article parsing completed in {parsing_time:.2f} seconds")
        
        # Clear parsing flag
        if "parsing_article" in st.session_state:
            print(f"✅ Clearing parsing flag after successful parsing")
            del st.session_state.parsing_article
            
        if parsed and parsed.get('text'):
            # Show some content stats
            content_text = parsed.get('text', '')
            word_count = len(content_text.split())
            char_count = len(content_text)
            
            # Log content statistics
            print(f"📊 Article stats: {char_count} chars, {word_count} words")
            parsing_progress.success(f"✅ Successfully parsed: {word_count} words, {char_count} chars")
            
            if word_count > 3000:
                st.warning(f"⚠️ Article is very long ({word_count} words). Processing may take longer.")
                
            return {
                'title': parsed.get('title', 'Untitled'),
                'text': content_text,
                'html': parsed.get('html', ''),
                'markdown': parsed.get('markdown', ''),
                'url': url,
                'word_count': word_count,
                'parsing_time': parsing_time
            }
        else:
            error_msg = f"❌ Could not extract content from: {url}"
            print(error_msg)
            parsing_progress.error(error_msg)
            
            # Clear parsing flag on error
            if "parsing_article" in st.session_state:
                del st.session_state.parsing_article
            return None
    except Exception as e:
        error_msg = f"❌ Error processing {url}: {str(e)}"
        print(error_msg)
        print(f"📋 Traceback: {traceback.format_exc()}")
        parsing_progress.error(error_msg)
        
        # Clear parsing flag on error
        if "parsing_article" in st.session_state:
            del st.session_state.parsing_article
        return None

def generate_script(content, content_agent):
    """Generate a script from article content."""
    try:
        # Convert content to SimilarArticle format
        similar_article = SimilarArticle(
            title=content['title'],
            content=content['text'],
            source="user_input",
            url=content['url'],
            similarity_score=1.0
        )
        
        # Generate content
        article = content_agent.generate_article_from_direct_sources(
            topic="Article Summary",
            similar_articles=[similar_article]
        )
        
        # Create script
        script = f"Title: {article['headline']}\n\n"
        script += f"{article['intro']}\n\n"
        script += f"{article['body']}\n\n"
        script += f"{article['conclusion']}"
        
        return {
            'content': script,
            'article': article
        }
    except Exception as e:
        st.error(f"Error generating script: {str(e)}")
        return None

def generate_audio(script_text, audio_agent):
    """Generate audio from script text."""
    try:
        # Create an AudioRequest object
        audio_request = AudioRequest(
            text=script_text,
            title=script_text.split('\n')[0].replace('Title: ', ''),
            voice_id=audio_agent.voice_id,
            output_dir="generated_audio",
            upload_to_s3=True,
            s3_bucket="vectorverseevolve",
            s3_region="us-west-2"
        )
        
        # Generate audio content
        audio_content = audio_agent.generate_audio_content(audio_request)
        
        return {
            'audio_file': audio_content.audio_file,
            'audio_url': audio_content.audio_url if hasattr(audio_content, 'audio_url') else None,
            'script_file': audio_content.script_file,
            'srt_file': audio_content.srt_file
        }
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

def generate_avatar_video(audio_url, avatar_id=None, poll_for_completion=True, poll_interval=15, max_attempts=20, indefinite_polling=True):
    """Generate avatar video from audio."""
    try:
        # Get video URL from avatar ID or use default
        video_url = SYNC_AVATAR_MAP.get(avatar_id) if avatar_id else SYNC_AVATARS[0]['video_url']
        
        # Generate video with polling parameters
        video_result = avatar_agent.generate_video(
            audio_url=audio_url,
            video_url=video_url,
            poll_for_completion=poll_for_completion,
            poll_interval=poll_interval,
            max_attempts=max_attempts,
            indefinite_polling=indefinite_polling
        )
        
        return video_result
    except Exception as e:
        st.error(f"Error generating video: {str(e)}")
        return None

# Initialize session state for app selection
if "current_app" not in st.session_state:
    st.session_state.current_app = "content_generator"

def show_content_generator():
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
            
            process_articles(articles, selected_voice, use_avatar)

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
                
                process_articles([article], selected_voice, use_avatar)

def process_articles(articles, selected_voice="Rachel", use_avatar=False):
    """Process a list of articles to generate content, audio, and avatar."""
    if articles:
        # Store articles
        db_agent.store_articles(articles)
        st.success(f"Stored {len(articles)} articles")
        
        # Instead of search_query, use the actual articles directly
        st.write("Generating summary for submitted article(s)...")
        
        # Convert raw articles to SimilarArticle format directly
        # This ensures we summarize the exact articles the user submitted
        similar_articles = []
        for article in articles:
            similar_articles.append(SimilarArticle(
                title=article.title,
                content=article.content.text,
                source=article.source,
                url=article.link,
                similarity_score=1.0  # Perfect match since it's the exact article
            ))
        
        # Generate content using the exact articles submitted
        article = content_agent.generate_article_from_direct_sources(
            topic="Article Summary", 
            similar_articles=similar_articles
        )
        
        # Display generated content
        st.header("Generated Content")
        st.subheader(article['headline'])
        st.write(article['intro'])
        st.write(article['body'])
        st.write(article['conclusion'])
        
        # Generate audio with selected voice
        with st.spinner("Generating audio..."):
            audio_agent.voice_id = VOICES[selected_voice]
            
            # Create a script from the article content
            script = f"Title: {article['headline']}\n\n"
            script += f"{article['intro']}\n\n"
            script += f"{article['body']}\n\n"
            script += f"{article['conclusion']}"
            
            # Create an AudioRequest object
            audio_request = AudioRequest(
                text=script,
                title=article['headline'],
                voice_id=audio_agent.voice_id,
                output_dir="generated_audio",
                upload_to_s3=True,  # Always upload to S3
                s3_bucket="vectorverseevolve",
                s3_region="us-west-2"
            )
            
            # Generate audio content
            audio_content = audio_agent.generate_audio_content(audio_request)
            
            # Display audio and transcripts
            st.header("Audio Content")
            st.audio(audio_content.audio_file)
            
            with st.expander("View Script"):
                st.text(audio_content.script_text)
                
            with st.expander("View Subtitles"):
                st.text(open(audio_content.srt_file).read())

            # For avatar generation, always use the automatically generated audio URL
            st.subheader("Avatar Generation")
            
            # Always enable avatar video generation
            use_avatar = True
            enhance_face = True
            resolution = "full"
            
            # Use the audio_content.audio_url directly - no manual input needed
            working_s3_url = audio_content.audio_url if hasattr(audio_content, 'audio_url') and audio_content.audio_url else None
            
            if working_s3_url:
                st.success(f"✅ Using audio file: {os.path.basename(audio_content.audio_file)}")
                st.code(working_s3_url, language="text")
            else:
                # Attempt to upload the file again if no URL is available
                try:
                    from audio_generator import upload_file_to_s3
                    working_s3_url = upload_file_to_s3(
                        file_path=audio_content.audio_file,
                        s3_key=os.path.basename(audio_content.audio_file),
                        bucket_name="vectorverseevolve",
                        region="us-west-2"
                    )
                    if working_s3_url:
                        st.success(f"✅ Audio file uploaded to S3: {working_s3_url}")
                        # Update the audio content with the new URL
                        audio_content.audio_url = working_s3_url
                    else:
                        st.warning("⚠️ S3 upload failed. Avatar generation may not work correctly.")
                except Exception as e:
                    st.warning(f"⚠️ Could not upload to S3: {str(e)}. Avatar generation may not work correctly.")

            # Save results
            results = {
                "article": article,
                "audio": {
                    "file": audio_content.audio_file,
                    "script": audio_content.script_file,
                    "srt": audio_content.srt_file,
                    "voice": selected_voice
                },
                "metadata": {
                    "generated_date": datetime.now().isoformat(),
                    "source_type": articles[0].source_type,
                    "source": articles[0].source
                }
            }
            
            if articles[0].link:
                results["metadata"]["source_urls"] = [article.link for article in articles]
            
            # Save to file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"generated_content/content_{timestamp}.json"
            os.makedirs("generated_content", exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            # Add download button for results
            st.download_button(
                "Download Results",
                json.dumps(results, indent=2),
                file_name=f"content_{timestamp}.json",
                mime="application/json",
                key="download_results_button_main"
            )

    # After generating audio content
    if 'audio_content' in locals():
        # Add social media distribution section
        st.header("Social Media Distribution")
        
        # Platform selection
        platforms = st.multiselect(
            "Select platforms to publish to",
            options=list(social_agent.platforms.keys()),
            default=[],
            key="social_platform_select_main"
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
                index=options.index(default_personality) if default_personality in options else 0,
                key=f"personality_{platform}_main"
            )
            
            custom_personalities[platform] = selected
        
        # Schedule posting
        schedule = st.checkbox("Schedule for later", key="schedule_checkbox_main")
        post_time = None
        
        if schedule:
            post_time = st.date_input("Post date", key="post_date_picker_main") 
            post_hour = st.slider("Hour", 0, 23, 9, key="post_hour_slider_main")
            post_minute = st.slider("Minute", 0, 59, 0, step=5, key="post_minute_slider_main")
            post_time = datetime.combine(post_time, datetime.min.time()) + timedelta(hours=post_hour, minutes=post_minute)
            
            st.write(f"Scheduled for: {post_time.strftime('%Y-%m-%d %H:%M')}")
        
        # Post button
        if st.button("Post to Social Media", key="post_social_button_main"):
            with st.spinner("Posting to social media..."):
                # Prepare media files
                media_files = {
                    platform: [audio_content.audio_file] for platform in platforms
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

        # Generate avatar video if requested
        if use_avatar and 'audio_content' in locals() and len(avatar_agent.get_available_avatars()) > 0:
            # Use the provided S3 URL if available
            audio_url_for_avatar = working_s3_url if working_s3_url else None
            
            if not audio_url_for_avatar:
                st.warning("No valid S3 URL available for audio. Avatar generation requires a hosted audio file.")
            else:
                with st.spinner("Generating avatar video..."):
                    try:
                        # Get first available avatar
                        available_avatars = avatar_agent.get_available_avatars()
                        if not available_avatars:
                            st.error("No avatars available")
                            return
                            
                        # Use first available avatar
                        avatar_name = available_avatars[0]
                        
                        # Call with the correct parameters and the S3 URL
                        video_result = avatar_agent.generate_video(
                            audio_url=audio_url_for_avatar,
                            video_url=None,  # Use default video URL for the avatar
                            poll_for_completion=True,
                            poll_interval=15,
                            max_attempts=20,
                            indefinite_polling=True
                        )
                        
                        # Check if the video generation was successful
                        if video_result and video_result.video_url:
                            video_file = video_result.video_url
                            
                            # Display the video
                            st.header("Avatar Video")
                            st.success(f"✅ Video generation complete! Job ID: {video_result.job_id}")
                            st.video(video_file)
                            
                            # Include video in results
                            results["video"] = {
                                "file": video_file,
                            }
                            
                            # Add video to social media files
                            media_files = {
                                platform: [video_file] for platform in platforms
                            }
                        elif video_result.status == "FAILED" or video_result.status == "REJECTED":
                            st.error(f"Video generation failed: {video_result.error}")
                            st.info("You can try again with different settings.")
                        else:
                            # Create a placeholder for status updates
                            status_container = st.empty()
                            status_container.warning(f"Video generation started but is still processing. Job ID: {video_result.job_id}")
                            
                            # Create progress bar
                            progress_bar = st.progress(0)
                            
                            # Poll for job status updates without redirecting - indefinitely
                            attempt = 0
                            while True:
                                attempt += 1
                                # Use a logarithmic progress bar that approaches but never reaches 1.0
                                # This shows activity without implying completion
                                progress_value = min(0.9, 0.5 + (0.4 * math.log(attempt + 1) / math.log(100)))
                                progress_bar.progress(progress_value)
                                
                                # Check status
                                job_status = avatar_agent.check_job_status(video_result.job_id)
                                status = job_status.get("status", "UNKNOWN")
                                
                                if status == "COMPLETED" and job_status.get("outputUrl"):
                                    # Job completed successfully
                                    progress_bar.progress(1.0)
                                    video_url = job_status.get("outputUrl")
                                    
                                    # Download the video
                                    try:
                                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                        download_path = f"generated_videos/sync_video_{timestamp}.mp4"
                                        os.makedirs("generated_videos", exist_ok=True)
                                        
                                        # Create authentication token header
                                        headers = {"x-api-key": avatar_agent.sync_api_key}
                                        
                                        with requests.get(video_url, headers=headers, stream=True) as r:
                                            r.raise_for_status()
                                            with open(download_path, 'wb') as f:
                                                for chunk in r.iter_content(chunk_size=8192):
                                                    f.write(chunk)
                                        
                                        # Upload to S3
                                        from audio_generator import upload_file_to_s3
                                        s3_video_url = upload_file_to_s3(
                                            file_path=download_path,
                                            s3_key=os.path.basename(download_path),
                                            bucket_name="vectorverseevolve",
                                            region="us-west-2"
                                        )
                                        
                                        # Update status and display video
                                        status_container.success(f"✅ Video generation complete! Job ID: {video_result.job_id}")
                                        st.video(s3_video_url)
                                        
                                        # Include video in results
                                        results["video"] = {
                                            "file": s3_video_url,
                                        }
                                        
                                        # Add video to social media files
                                        media_files = {
                                            platform: [s3_video_url] for platform in platforms
                                        }
                                        
                                        break
                                    except Exception as e:
                                        status_container.error(f"Error processing completed video: {str(e)}")
                                        break
                                
                                elif status in ["FAILED", "REJECTED"]:
                                    # Job failed
                                    error_message = job_status.get("error", "Unknown error")
                                    status_container.error(f"Video generation failed: {error_message}")
                                    break
                                
                                # Update status message
                                elapsed_time = attempt * 15
                                status_container.warning(f"Video generation in progress ({status}). Job ID: {video_result.job_id}\nProcessing for {elapsed_time} seconds...")
                                
                                # Wait before checking again
                                time.sleep(15)
                    except Exception as e:
                        st.error(f"Error generating avatar video: {str(e)}")
                        print(f"📋 Traceback: {traceback.format_exc()}")

def show_news_to_avatar():
    st.title("News to Avatar Video Generator")
    
    # Add clear app identification banner
    st.markdown(
        """
        <div style="background-color:#ff4b4b; padding:10px; border-radius:10px; margin-bottom:10px;">
            <h3 style="color:white; margin:0; text-align:center;">🎬 NEWS TO AVATAR</h3>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # Initialize session state variables
    if "generated_audio" not in st.session_state:
        st.session_state.generated_audio = None
    if "generated_audio_url" not in st.session_state:
        st.session_state.generated_audio_url = None
    if "job_id" not in st.session_state:
        st.session_state.job_id = None
    if "job_status" not in st.session_state:
        st.session_state.job_status = None
    if "video_result" not in st.session_state:
        st.session_state.video_result = None
    
    # Create tabs for different sections
    news_tab, generate_tab, jobs_tab = st.tabs(["📰 News", "📺 Generate", "🔄 Job Management"])
    
    with news_tab:
        # News input section
        url_input = st.text_input(
            "Enter article URL:",
            value="https://techcrunch.com/2025/04/07/ibm-acquires-consultancy-hakkoda-as-it-continues-its-ai-investment-push/",
            help="Enter a URL to a news article to process"
        )
        
        if st.button("🔍 Parse Article"):
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
                            st.success("✅ Article processed successfully! Switch to Generate tab to create video.")
    
    with generate_tab:
        # Avatar selection and video generation
        st.subheader("👤 Avatar Selection")
        
        # Display available avatars
        for avatar in SYNC_AVATARS:
            st.write(f"**{avatar['name']}**")
            if avatar['image_url']:
                st.image(avatar['image_url'], width=150)
            st.write(avatar['description'])
        
        # Generate video button
        if st.session_state.generated_audio_url:
            if st.button("🎬 Generate Video"):
                with st.spinner("Generating avatar video..."):
                    video_result = generate_avatar_video(
                        audio_url=st.session_state.generated_audio_url,
                        avatar_id=SYNC_AVATARS[0]['id']  # Using first avatar by default
                    )
                    if video_result and video_result.video_url:
                        st.success("✅ Video generated successfully!")
                        st.video(video_result.video_url)
        else:
            st.warning("⚠️ Please generate audio content in the News tab first.")
    
    with jobs_tab:
        # Job management section
        st.subheader("Recent Jobs")
        jobs = avatar_agent.list_saved_jobs()
        if jobs:
            for job in jobs:
                st.write(f"Job ID: {job['id']}")
                st.write(f"Status: {job['status']}")
                if job['status'] == "COMPLETED" and job.get('video_url'):
                    st.video(job['video_url'])
        else:
            st.info("No jobs found. Generate some videos first!")

def main():
    # Validate conda environment
    validate_conda_env()
    
    # Check if we need to reset state
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
        
        print(f"⏱️ Article parsing in progress for {elapsed_seconds:.1f} seconds: {st.session_state.processing_url}")
        
        if elapsed_seconds > 120:
            print(f"🛑 Article parsing has been stuck for {elapsed_seconds:.1f} seconds - resetting state")
            st.warning(f"⚠️ Article parsing has been running for too long ({int(elapsed_seconds)} seconds). Resetting state...")
            reset_session_state()
    elif "parsing_started_at" in st.session_state and "parsing_article" not in st.session_state:
        # Clean up the timestamp if parsing is done
        print("🧹 Cleaning up parsing timestamp - parsing is finished")
        del st.session_state.parsing_started_at
    
    # Also check job status for completion
    if "job_status" in st.session_state and st.session_state.job_status in ["COMPLETED", "completed"]:
        print("✅ Job completed - setting needs_reset flag for next reload")
        # Set a flag to reset on next reload
        st.session_state.needs_reset = True
        st.session_state.reset_after_completion = True
    
    # Check if running on Digital Ocean
    is_digital_ocean = os.environ.get("PORT") is not None
    
    if is_digital_ocean:
        # Use the PORT environment variable provided by Digital Ocean
        port = int(os.environ.get("PORT", 8080))
        # Set Streamlit server port
        os.environ['STREAMLIT_SERVER_PORT'] = str(port)
        # Set other Streamlit configurations for production
        os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
        os.environ['STREAMLIT_SERVER_HEADLESS'] = 'true'
        os.environ['STREAMLIT_SERVER_FILE_WATCHER_TYPE'] = 'none'
    
    # Add app selector in sidebar
    st.sidebar.title("App Selection")
    app_options = {
        "content_generator": "📝 Content Generator",
        "news_to_avatar": "🎬 News to Avatar"
    }
    
    selected_app = st.sidebar.radio(
        "Choose Interface:",
        list(app_options.keys()),
        format_func=lambda x: app_options[x],
        key="app_selector"
    )
    
    # Add Reset button in sidebar
    st.sidebar.title("🛠️ Tools")
    if st.sidebar.button("🔄 Reset App State", help="Use this if the app gets stuck"):
        print("🔄 Manual reset button pressed")
        reset_session_state()
    
    # Show the selected interface
    if selected_app == "content_generator":
        show_content_generator()
    else:
        show_news_to_avatar()

if __name__ == "__main__":
    main() 
