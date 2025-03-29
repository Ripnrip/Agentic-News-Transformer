"""News to Avatar Pipeline - Convert news articles to lip-synced avatar videos."""
import os
import streamlit as st

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

# Initialize agents
@st.cache_resource
def init_agents():
    """Initialize all required agents."""
    news_agent = NewsSearchAgent(article_limit=1)  # We only need one article at a time
    content_agent = ContentGenerationAgent()
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
            output_dir="generated_audio"
        )
        
        # Generate audio
        result = audio_agent.generate_audio_content(request)
        
        if result and hasattr(result, 'audio_file'):
            st.success("Audio generated successfully!")
            return result.audio_file
        else:
            st.error("Failed to generate audio: No audio file in result")
            return None
    except Exception as e:
        st.error(f"Error generating audio: {str(e)}")
        return None

def generate_avatar_video(audio_file, avatar_name, sync_api_key, 
                      poll_for_completion=True, poll_interval=10, 
                      indefinite_polling=False, max_attempts=30, audio_url=None):
    """Generate lip-synced video using Sync.so API."""
    try:
        # Log start of video generation process
        print(f"🎬 Starting video generation for audio: {audio_file}")
        print(f"🤖 Using avatar: {avatar_name}")
        
        # Check if audio file exists
        if not os.path.exists(audio_file):
            print(f"❌ Error: Audio file not found: {audio_file}")
            return None
        
        # Initialize avatar generation agent
        print(f"🔄 Initializing avatar generation agent...")
        avatar_agent = AvatarGenerationAgent()
        
        # Generate video
        print(f"🎥 Generating video with settings: poll_for_completion={poll_for_completion}, poll_interval={poll_interval}, indefinite_polling={indefinite_polling}")
        video_result = avatar_agent.generate_video(
            audio_file=audio_file,
            avatar_name=avatar_name,
            poll_for_completion=poll_for_completion,
            poll_interval=poll_interval,
            indefinite_polling=indefinite_polling,
            max_attempts=max_attempts,
            audio_url=audio_url
        )
        
        # Log success or failure
        if video_result and video_result.video_url:
            print(f"✅ Video generation successful! URL: {video_result.video_url}")
            return video_result
        elif video_result:
            print(f"⏳ Video generation job submitted with ID: {video_result.job_id}, Status: {video_result.status}")
            return video_result
        else:
            print(f"❌ Video generation failed with unknown error.")
            return None
    except Exception as e:
        print(f"❌ Error in video generation: {str(e)}")
        traceback.print_exc()
        return None

def main():
    """Run the app."""
    # Validate conda environment
    #validate_conda_env()
    
    # Initialize agents
    news_agent, content_agent, audio_agent, avatar_agent = init_agents()
    
    st.title("📺 News to Avatar Generator")
    st.write("Convert news articles to avatar videos with AI-generated scripts and lip-syncing.")
    
    # Set up tabs
    tab1, tab2, tab3 = st.tabs(["📰 News", "📺 Generate", "🔄 Job Management"])
    
    # News tab
    with tab1:
        # Get article URL
        article_url = st.text_input(
            "Enter a news article URL:", 
            value="https://www.theguardian.com/commentisfree/ng-interactive/2025/mar/28/ai-alphafold-biology-protein-structure",
            help="Paste a URL to a news article"
        )
        
        if st.button("🔍 Parse Article", use_container_width=True):
            # Status indicators
            status_area = st.container()
            article_status = status_area.empty()
            script_status = status_area.empty()
            audio_status = status_area.empty()
            video_status = status_area.empty()
            
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
                        audio_file = generate_audio(script_result.content, audio_agent)
                        
                        if audio_file:
                            audio_status.success("🎵 Audio: Generated ✅")
                            
                            # Save to session state for the Generate tab
                            st.session_state.generated_audio = audio_file
                            
                            # Show audio player in expandable section
                            with st.expander("🔊 Generated Audio"):
                                st.audio(audio_file)
                                
    # Generate tab                            
    with tab2:
        st.subheader("🎬 Video Generation")
        
        # Initialize avatar agent if needed
        if "avatar_agent" not in locals():
            avatar_agent = AvatarGenerationAgent()
        
        # Check if audio file exists in session state
        audio_file = None
        if hasattr(st.session_state, 'generated_audio'):
            audio_file = st.session_state.generated_audio
        
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
        
        if audio_file:
            # Avatar section
            st.subheader("👱‍♀️ Avatar")
            available_avatars = avatar_agent.get_available_avatars()
            selected_avatar = available_avatars[0]  # Auto-select the only avatar
            
            # Show avatar info
            st.write("Using avatar:")
            col1, col2 = st.columns([1, 2])
            with col1:
                # Show avatar preview image
                avatar_info = avatar_agent.get_avatar_info(selected_avatar)
                if avatar_info and "image" in avatar_info:
                    st.image(avatar_info["image"], width=200)
            with col2:
                st.write(f"**Name:** {selected_avatar}")
                st.write(f"**Style:** {avatar_info['style']}")
                st.write(f"**Personality:** {avatar_info['personality']}")
                st.write(f"**Description:** {avatar_info['description']}")
            
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
            
            # Add option for providing public audio URL
            st.subheader("📝 Audio Options")
            
            # Pre-defined S3 URLs
            preset_audio_url = "https://vectorverseevolve.s3.us-west-2.amazonaws.com/News_Script_20250329_033235.mp3"
            
            st.info("""
            ### Audio URL Required
            
            Sync.so requires all audio files to be hosted on publicly accessible URLs.
            
            We'll use a pre-configured S3 URL for testing:
            """)
            
            # Generate a suggested filename based on timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suggested_name = f"News_Script_{timestamp}.mp3"
            suggested_url = f"https://vectorverseevolve.s3.us-west-2.amazonaws.com/{suggested_name}"
            
            audio_url_option = st.radio(
                "Choose audio URL option:",
                ["Use existing S3 URL", "Input custom URL"],
                index=0  # Default to using existing URL
            )
            
            if audio_url_option == "Use existing S3 URL":
                audio_public_url = preset_audio_url
                st.success(f"Using: {audio_public_url}")
            else:
                audio_public_url = st.text_input(
                    "Custom audio URL:", 
                    value=suggested_url,
                    help="URL to your audio file hosted on AWS S3 or other public service"
                )
                
                st.info(f"""
                **To use a custom URL:**
                1. Upload the audio file at: `{audio_file}`
                2. To a public hosting service (AWS S3, etc.)
                3. Make it publicly accessible
                4. Enter the URL above
                """)
            
            if not audio_public_url:
                st.error("Please provide a URL for your audio file")
                audio_public_url = None
            
            if st.button("Generate Video with Sync.so", use_container_width=True):
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
                        audio_url=audio_public_url  # Always pass the URL, even if None
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
                                st.write("**Video URL:**")
                                st.code(video_result.video_url)
                                st.write("**Preview:**")
                                st.video(video_result.video_url)
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
                    else:
                        video_status.error("🎥 Video: Failed ❌")
                        progress_bar.progress(0)
                        debug_status.error("❌ Video generation failed")
                        completion_status.error("❌ Failed to generate video. Check debug information above.")

    # Job management tab
    with tab3:
        st.title("🔄 Job Management")
        st.write("View and manage your Sync.so video generation jobs.")
        
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
                    
                    # Show raw data in expander
                    with st.expander("Raw Job Data"):
                        st.json(job_info)
                else:
                    st.warning(f"Job file not found for ID {job_id}")
            else:
                st.info("Select a job from the list to view details.")

if __name__ == "__main__":
    main() 