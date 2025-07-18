"""News to Avatar Pipeline - Convert news articles to lip-synced avatar videos."""
import os
import streamlit as st
import urllib.parse

# Set page config at the very beginning
st.set_page_config(
    page_title="News to Avatar",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

from agents import NewsSearchAgent
from content_generator import ContentGenerationAgent, ArticleRequest
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent, VideoSettings
import json
from datetime import datetime
from env_validator import validate_conda_env
import traceback

# Initialize session state for tab selection and caching
if 'current_tab' not in st.session_state:
    st.session_state.current_tab = 0  # Default to News tab (first tab)

# Add URL caching to avoid reprocessing the same articles
if 'processed_urls' not in st.session_state:
    st.session_state.processed_urls = {}  # Dictionary to cache processed URLs

# Initialize agents
@st.cache_resource
def init_agents():
    """Initialize all required agents."""
    from database_agent import DatabaseAgent
    
    news_agent = NewsSearchAgent(article_limit=1)  # We only need one article at a time
    db_agent = DatabaseAgent()
    content_agent = ContentGenerationAgent(db_agent)
    audio_agent = AudioGenerationAgent()
    avatar_agent = AvatarGenerationAgent()
    return news_agent, content_agent, audio_agent, avatar_agent

def process_article_url(url, news_agent):
    """Process article URL using NewsSearchAgent."""
    try:
        # Create a simple article object with the URL
        from dataclasses import dataclass
        from datetime import datetime
        
        @dataclass
        class Article:
            title: str = "User Provided Article"
            link: str = url
            source: str = "User Input"
            published_date: datetime = datetime.now()
            source_type: str = "web"
            author: str = "Unknown"
            engagement: dict = None
        
        article = Article(link=url)
        
        # Use the existing parsing functionality
        parsing_results = news_agent.fetch_and_parse_articles([article], timeout_minutes=15)
        
        if parsing_results["parsed"]:
            # Get the parsed content
            parsed_content = parsing_results["parsed"][0]
            
            # Extract the text content
            if parsed_content.get("content"):
                content = parsed_content["content"]
                if content.get("markdown"):
                    return content["markdown"]
                elif content.get("html"):
                    return content["html"]
                elif content.get("text"):
                    return content["text"]
            
        st.error("Failed to parse article content")
        return None
        
    except Exception as e:
        st.error(f"Error processing article: {str(e)}")
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
        return None

def generate_avatar_video(audio_file, avatar_name, sync_api_key, 
                      poll_for_completion=True, poll_interval=10, 
                      indefinite_polling=False, max_attempts=30, audio_url=None):
    """Generate a lip-synced avatar video."""
    try:
        print(f"🎬 Starting video generation for audio: {audio_file}")
        print(f"🤖 Using avatar: {avatar_name}")
        
        # Initialize avatar generation agent
        print(f"🔄 Initializing avatar generation agent...")
        avatar_agent = AvatarGenerationAgent()
        
        # Set up video generation settings
        print(f"🎥 Generating video with settings: poll_for_completion={poll_for_completion}, poll_interval={poll_interval}, indefinite_polling={indefinite_polling}")
        
        # Ensure audio URL is properly encoded (but not double-encoded)
        if audio_url:
            # First decode the URL in case it's already encoded to prevent double encoding
            import urllib.parse
            try:
                # Try to decode the URL first to ensure we don't double-encode
                decoded_url = urllib.parse.unquote(audio_url)
                
                # Now parse and properly encode it exactly once
                parsed_url = urllib.parse.urlparse(decoded_url)
                path = urllib.parse.quote(parsed_url.path)
                
                # Reconstruct the URL with a properly encoded path
                audio_url = urllib.parse.urlunparse((
                    parsed_url.scheme,
                    parsed_url.netloc,
                    path,
                    parsed_url.params,
                    parsed_url.query,
                    parsed_url.fragment
                ))
                
                print(f"🔊 Using properly encoded audio URL: {audio_url}")
            except Exception as e:
                print(f"⚠️ Warning during URL encoding: {str(e)}")
        
        # Generate settings
        settings = VideoSettings(
            model="lipsync-1.9.0-beta",
            output_format="mp4",
            resolution="portrait",
            width=480,
            height=854  # 9:16 aspect ratio for portrait videos
        )
        
        # Generate video
        result = avatar_agent.generate_video(
            audio_file=audio_file,
            avatar_name=avatar_name,
            settings=settings,
            poll_for_completion=poll_for_completion,
            poll_interval=poll_interval,
            indefinite_polling=indefinite_polling,
            max_attempts=max_attempts,
            audio_url=audio_url
        )
        
        return result
    except Exception as e:
        print(f"❌ Error generating avatar video: {str(e)}")
        st.error(f"❌ Error generating avatar video: {str(e)}")
        return None

def main():
    """Run the app."""
    # Validate conda environment
    #validate_conda_env()
    
    # Check if we need to switch tabs
    if 'switch_to_tab' in st.session_state:
        # Get the target tab index
        target_tab = st.session_state.switch_to_tab
        # Update the current tab
        st.session_state.current_tab = target_tab
        # Clear the switch flag to prevent loops
        del st.session_state.switch_to_tab
        
    # Initialize agents
    news_agent, content_agent, audio_agent, avatar_agent = init_agents()
    
    st.title("📺 News to Avatar Generator")
    st.write("Convert news articles to avatar videos with AI-generated scripts and lip-syncing.")
    
    # Create tabs based on session state
    tabs = st.tabs(["📰 News", "📺 Generate", "🔄 Job Management"])
    
    # News tab (only displayed if selected)
    with tabs[0]:
        if st.session_state.current_tab == 0:
            # Get article URL
            article_url = st.text_input(
                "Enter a news article URL:", 
                value="https://www.theguardian.com/commentisfree/ng-interactive/2025/mar/28/ai-alphafold-biology-protein-structure",
                help="Paste a URL to a news article"
            )
            
            # Check if we've already processed this URL
            if article_url in st.session_state.processed_urls:
                cached_data = st.session_state.processed_urls[article_url]
                st.success(f"✅ Using cached data for: {article_url}")
                
                # Display cached data
                with st.expander("📄 Cached Script"):
                    st.write(f"**Title:** {cached_data['title']}")
                    st.write("**Script:**")
                    st.write(cached_data['content'])
                    st.write("**Keywords:** " + ", ".join(cached_data['keywords']))
                
                # Display cached audio
                with st.expander("🔊 Cached Audio"):
                    st.audio(cached_data['audio_file'])
                
                # Add button to use cached data
                if st.button("Use Cached Data for Video Generation", use_container_width=True):
                    st.session_state.generated_audio = cached_data['audio_file']
                    st.session_state.generated_audio_url = cached_data['audio_url']
                    # Set tab to Generate and rerun
                    st.session_state.switch_to_tab = 1  # Switch to Generate tab
                    st.rerun()  # Use rerun instead of experimental_rerun
                    
                # Add back button to return to News tab
                if st.button("⬅️ Back to News"):
                    st.session_state.switch_to_tab = 0
                    st.rerun()
            
            # Parse Article button
            if st.button("🔍 Parse Article", use_container_width=True):
                # Status indicators
                status_area = st.container()
                article_status = status_area.empty()
                script_status = status_area.empty()
                audio_status = status_area.empty()
                
                # Create a progress bar
                progress_bar = st.progress(0)
                
                # Debug status
                debug_status = st.empty()
                
                if article_url:
                    # Process article
                    article_status.warning("📰 Article: Parsing...")
                    progress_bar.progress(25)
                    
                    content = process_article_url(article_url, news_agent)
                    
                    if content:
                        article_status.success("📰 Article: Parsed ✅")
                        progress_bar.progress(50)
                        debug_status.success(f"✅ Article parsed successfully from {article_url}")
                        
                        # Generate script
                        script_status.warning("📝 Script: Generating...")
                        script_result = generate_script(content, content_agent)
                        
                        if script_result:
                            script_status.success("📝 Script: Generated ✅")
                            progress_bar.progress(75)
                            debug_status.success("✅ Script generated successfully")
                            
                            # Show script in expandable section
                            with st.expander("📄 Generated Script"):
                                st.write(f"**Title:** {script_result.title}")
                                st.write("**Script:**")
                                st.write(script_result.content)
                                st.write("**Keywords:** " + ", ".join(script_result.keywords))
                            
                            # Generate audio
                            audio_status.warning("🎵 Audio: Generating...")
                            audio_result = generate_audio(script_result.content, audio_agent)
                            
                            if audio_result:
                                audio_status.success("🎵 Audio: Generated ✅")
                                
                                # Save to session state for the Generate tab
                                st.session_state.generated_audio = audio_result['audio_file']
                                st.session_state.generated_audio_url = audio_result['audio_url']
                                
                                # Cache the results
                                st.session_state.processed_urls[article_url] = {
                                    'title': script_result.title,
                                    'content': script_result.content,
                                    'keywords': script_result.keywords,
                                    'audio_file': audio_result['audio_file'],
                                    'audio_url': audio_result['audio_url'],
                                    'timestamp': datetime.now().isoformat()
                                }
                                
                                # Show audio player in expandable section
                                with st.expander("🔊 Generated Audio"):
                                    st.audio(audio_result['audio_file'])
                                
                                # Auto-switch to Generate tab
                                st.success("✅ All processing complete! Switching to Video Generation tab...")
                                # Set flag to switch tabs on next execution - safer than immediate rerun
                                st.session_state.switch_to_tab = 1  # Generate tab
                                # Use rerun() (not experimental_rerun)
                                st.rerun()

    # Generate tab                            
    with tabs[1]:
        if st.session_state.current_tab == 1:  # Only show content if this tab is active
            st.subheader("🎬 Video Generation")
            
            # Initialize avatar agent if needed
            if "avatar_agent" not in locals():
                avatar_agent = AvatarGenerationAgent()
            
            # Check if audio file exists in session state
            audio_file = None
            audio_url = None
            
            if hasattr(st.session_state, 'generated_audio'):
                audio_file = st.session_state.generated_audio
                
            if hasattr(st.session_state, 'generated_audio_url'):
                audio_url = st.session_state.generated_audio_url
                if audio_url:
                    st.success(f"✅ Using automatically uploaded audio URL: {audio_url}")
            
            if not audio_file:
                # Allow manual audio upload as fallback
                st.warning("No generated audio found. Please generate a script and audio in the News tab or upload an audio file below.")
                
                uploaded_file = st.file_uploader("Upload an audio file (MP3):", type=["mp3"])
                if uploaded_file:
                    # Save uploaded file to disk
                    audio_dir = "generated_audio"
                    os.makedirs(audio_dir, exist_ok=True)
                    audio_file = os.path.join(audio_dir, "uploaded_audio.mp3")
                    
                    with open(audio_file, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    
                    st.success(f"Audio file uploaded and saved to {audio_file}")
                    
                    # Add back button to return to News tab
                    if st.button("⬅️ Back to News"):
                        st.session_state.switch_to_tab = 0
                        st.rerun()  # Use rerun instead of experimental_rerun
            
            # Avatar selection
            st.subheader("👤 Avatar Selection")
            
            # Get available avatars
            avatars = avatar_agent.get_available_avatars()
            
            if not avatars:
                st.error("No avatars found! Please check the `avatars` directory.")
                return
            
            # Get avatar info dictionary for each avatar name
            avatar_info_dict = {}
            for avatar_name in avatars:
                avatar_info_dict[avatar_name] = avatar_agent.get_avatar_info(avatar_name)
            
            # Display avatars with images if available
            avatar_cols = st.columns(len(avatars))
            
            for i, avatar_name in enumerate(avatars):
                with avatar_cols[i]:
                    st.write(f"**{avatar_name}**")
                    
                    avatar_info = avatar_info_dict[avatar_name]
                    # Try to display image if available
                    image_path = avatar_info.get("image")
                    if image_path and os.path.exists(image_path):
                        st.image(image_path, width=150)
                    elif image_path and image_path.startswith("http"):
                        st.image(image_path, width=150)
                    else:
                        st.info(f"[No preview image]")
                    
                    st.write(avatar_info.get("description", ""))
            
            # Avatar selection dropdown
            selected_avatar = st.selectbox(
                "Select Avatar:", 
                avatars,
                index=0
            )
            
            if not audio_file:
                st.warning("⚠️ Please generate or upload an audio file before proceeding.")
                # Add back button to return to News tab
                if st.button("⬅️ Back to News Tab"):
                    st.session_state.switch_to_tab = 0
                    st.rerun()  # Use rerun instead of experimental_rerun
                return
            
            # Add generation options
            with st.expander("⚙️ Generation Options", expanded=True):
                poll_option = st.radio(
                    "Generation Mode:",
                    ["Submit job and continue", "Wait with timeout", "Wait indefinitely"],
                    index=0,  # Default to submit and continue
                    help="Choose whether to wait for the video to complete or submit the job and check later"
                )
                
                poll_interval = st.slider(
                    "Poll Interval (seconds):",
                    min_value=5,
                    max_value=60,
                    value=15,
                    help="How often to check job status if waiting for completion"
                )
                
                max_attempts = st.slider(
                    "Maximum Polls:",
                    min_value=5,
                    max_value=120,
                    value=40,
                    help="Maximum number of times to check status (ignored if waiting indefinitely)"
                )
                
                estimated_time = max_attempts * poll_interval
                st.info(f"With these settings, will poll for up to {estimated_time} seconds (~{estimated_time/60:.1f} minutes)")
            
            # Process polling options
            poll_for_completion = poll_option in ["Wait with timeout", "Wait indefinitely"]
            indefinite_polling = poll_option == "Wait indefinitely"
            
            # Add option for providing public audio URL - only if we don't already have one
            if not audio_url:
                st.subheader("📝 Audio URL Options")
                
                # For audio, we need to use a public URL 
                # Since we don't have direct upload support, we'll use a hosted solution
                st.error("⚠️ Audio file must be hosted on a public URL to work with Sync.so")
                st.info("""
                ### Upload Steps:
                1. Upload your audio file to AWS S3 or similar service
                2. Make it publicly accessible
                3. Copy the public URL here
                
                Sync.so cannot access files from your local machine.
                """)
                
                base_filename = os.path.basename(audio_file)
                # Keep spaces in the suggested filename (don't replace with underscores)
                suggested_name = f"News Script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                audio_url = st.text_input(
                    "Enter public URL for your audio file:",
                    value=f"https://vectorverseevolve.s3.us-west-2.amazonaws.com/{urllib.parse.quote(suggested_name)}",
                    help="Upload your audio file to AWS S3 and enter the URL here"
                )
                
                if not audio_url:
                    st.error("Please provide a public URL for your audio file")
                    return None
                
                st.warning(f"""
                ⚠️ Please ensure that you've uploaded your audio file to:
                **{audio_url}**
                
                The file must be publicly accessible. This is a requirement from Sync.so.
                """)
            
            if st.button("Generate Video ", use_container_width=True):
                video_status = st.empty()
                progress_bar = st.progress(0)
                debug_status = st.empty()
                
                video_status.warning("🎥 Video: Starting generation process...")
                progress_bar.progress(80)
                
                # Create status containers
                upload_status = st.empty()
                processing_status = st.empty()
                completion_status = st.empty()
                
                with st.spinner("🎥 Creating lip-synced video..."):
                    # Generate video with options
                    video_result = generate_avatar_video(
                        audio_file,
                        selected_avatar,
                        None,  # API key is handled in the agent
                        poll_for_completion=poll_for_completion,
                        poll_interval=poll_interval,
                        indefinite_polling=indefinite_polling,
                        max_attempts=max_attempts,
                        audio_url=audio_url  # Use the audio URL (either from S3 upload or manual input)
                    )
                    
                    if video_result:
                        if video_result.status == "COMPLETED" and video_result.video_url:
                            # Video completed successfully
                            video_status.success("🎥 Video: Done ✅")
                            progress_bar.progress(100)
                            debug_status.success(f"✅ Video generated: {video_result.video_url}")
                            
                            # Show completion message
                            completion_status.success("✨ Video generation completed!")
                            
                            # Show video details
                            with st.expander("🎬 Final Video", expanded=True):
                                st.write("**Sync.so Video URL:**")
                                st.code(video_result.video_url)
                                
                                if video_result.s3_video_url:
                                    st.write("**S3 Backup URL:**")
                                    st.code(video_result.s3_video_url)
                                    st.success("✅ Video successfully backed up to S3!")
                                
                                st.write("**Preview:**")
                                st.video(video_result.video_url)
                                
                                # Add button to switch to Job Management tab
                                if st.button("View All Jobs"):
                                    st.session_state.switch_to_tab = 2  # Switch to Job Management tab
                                    st.rerun()  # Use rerun instead of experimental_rerun
                        else:
                            # Job submitted but not completed yet
                            video_status.info("🎥 Video: Job submitted ⏳")
                            progress_bar.progress(85)
                            debug_status.info(f"⏳ Job submitted with ID: {video_result.job_id}")
                            
                            # Show job information
                            completion_status.info(f"""
                                ### Job Submitted
                                
                                Your video generation job has been submitted to Sync.so.
                                
                                **Job ID:** `{video_result.job_id}`  
                                **Status:** {video_result.status}
                                
                                You can check the status of your job in the Job Management tab.
                            """)
                            
                            # Add button to switch to Job Management tab
                            if st.button("Go to Job Management"):
                                st.session_state.switch_to_tab = 2  # Switch to Job Management tab
                                st.rerun()  # Use rerun instead of experimental_rerun
                    else:
                        video_status.error("🎥 Video: Failed ❌")
                        progress_bar.progress(0)
                        debug_status.error("❌ Video generation failed")
                        completion_status.error("❌ Failed to generate video. Check debug information above.")

    # Job management tab
    with tabs[2]:
        if st.session_state.current_tab == 2:  # Only show content if this tab is active
            st.title("🔄 Job Management")
            st.write("View and manage your Sync.so video generation jobs.")
            
            # Add button to go back to News tab
            col1, col2 = st.columns([1, 6])
            with col1:
                if st.button("⬅️ Back to News"):
                    st.session_state.switch_to_tab = 0
                    st.rerun()  # Use rerun instead of experimental_rerun
            
            # Initialize avatar agent if needed
            if "avatar_agent" not in locals():
                avatar_agent = AvatarGenerationAgent()
            
            # Create two sections: Job List and Job Details
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.subheader("Jobs")
                # Display saved jobs
                saved_jobs = avatar_agent.list_saved_jobs()
                
                if not saved_jobs:
                    st.info("No jobs found. Generate some videos first!")
                else:
                    # Sort jobs by created_at (newest first)
                    saved_jobs.sort(key=lambda job: job.get('created_at', ''), reverse=True)
                    
                    for job in saved_jobs:
                        job_id = job.get('id', 'unknown')
                        status = job.get('status', 'UNKNOWN')
                        created_at = job.get('created_at', 'unknown')
                        
                        # Format created_at as date if possible
                        try:
                            created_date = datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            created_date = created_at
                        
                        # Show job entry with status color
                        if status == "COMPLETED":
                            st.success(f"Job: {job_id[:8]}... ({created_date})")
                        elif status in ["FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                            st.error(f"Job: {job_id[:8]}... ({created_date})")
                        else:
                            st.info(f"Job: {job_id[:8]}... ({created_date})")
                        
                        # Button to view job details
                        if st.button(f"View Job {job_id[:8]}...", key=f"view_{job_id}"):
                            st.session_state.selected_job_id = job_id
            
            with col2:
                st.subheader("Job Details")
                
                # Check for selected job
                if "selected_job_id" in st.session_state:
                    job_id = st.session_state.selected_job_id
                    
                    # Button to refresh job status
                    if st.button("Refresh Status"):
                        status_data = avatar_agent.check_job_status(job_id)
                        st.success("Job status refreshed!")
                        
                    # Display job details
                    job_file = os.path.join(avatar_agent.jobs_dir, f"{job_id}.json")
                    
                    if os.path.exists(job_file):
                        with open(job_file, "r") as f:
                            import json
                            job_info = json.load(f)
                        
                        # Display job info
                        st.write(f"**Job ID:** {job_id}")
                        st.write(f"**Created:** {job_info.get('created_at', 'unknown')}")
                        st.write(f"**Last Checked:** {job_info.get('last_checked', 'unknown')}")
                        st.write(f"**Status:** {job_info.get('status', 'UNKNOWN')}")
                        
                        # If job is completed, show the video
                        if job_info.get('status') == "COMPLETED" and job_info.get('data', {}).get('outputUrl'):
                            video_url = job_info.get('data', {}).get('outputUrl')
                            st.write("**Video:**")
                            st.video(video_url)
                        
                        # Show S3 URL if available
                        if job_info.get('s3_video_url'):
                            st.write("**S3 Backup URL:**")
                            st.code(job_info.get('s3_video_url'))
                            st.success("✅ Video backed up to S3")
                        
                        # Show raw data in expander
                        with st.expander("Raw Job Data"):
                            st.json(job_info)
                    else:
                        st.warning(f"Job file not found for ID {job_id}")
                else:
                    st.info("Select a job from the list to view details.")

if __name__ == "__main__":
    main() 