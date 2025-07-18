"""Agent for generating lip-synced avatar videos using local avatars and Sync.so API."""
import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
import requests
import streamlit as st
import boto3
import json
import urllib.parse

class VideoSettings(BaseModel):
    """Settings for video generation."""
    model: str = Field(default="lipsync-1.9.0-beta", description="Sync.so model to use")
    output_format: str = Field(default="mp4", description="Output video format")
    resolution: str = Field(default="portrait", description="Video resolution (portrait or landscape)")
    width: int = Field(default=480, description="Output width in pixels")
    height: int = Field(default=854, description="Output height in pixels")

class VideoResult(BaseModel):
    """Result of video generation."""
    job_id: str
    status: str
    video_url: Optional[str] = None
    s3_video_url: Optional[str] = None  # Added S3 URL field
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_completed(self) -> bool:
        """Check if video generation is completed."""
        return self.status == "COMPLETED" and self.video_url is not None

class AvatarGenerationAgent:
    """Agent for generating lip-synced avatar videos."""
    
    def __init__(self, api_key: str = None):
        """Initialize the avatar generation agent."""
        # Start initialization DEBUG marker
        print("===========================================================")
        print("🔑 DEBUG: Initializing AvatarGenerationAgent")
        
        # Get API key from environment or parameter
        self.sync_api_key = api_key or os.getenv("SYNC_SO_API_KEY")
        
        if self.sync_api_key:
            # Log that we found the key (without revealing the full key)
            key_length = len(self.sync_api_key)
            masked_key = f"{self.sync_api_key[:2]}...{self.sync_api_key[-3:]}" if key_length > 5 else "***"
            print(f"✅ SYNC_SO_API_KEY loaded: {masked_key} (length: {key_length})")
        else:
            print("❌ SYNC_SO_API_KEY not found! Set this environment variable to use Sync.so API.")
            
        # API configuration
        self.base_url = "https://api.sync.so/v2"
        self.headers = {
            "x-api-key": self.sync_api_key,
            "Content-Type": "application/json"
        }
        
        # Directory for storing video templates
        # Use a writable directory in the Digital Ocean environment
        # Default to 'avatars' in the current directory, but fall back to /tmp/avatars if permissions fail
        self.avatars_dir = os.getenv("AVATAR_DIR", "avatars")
        if not os.path.exists(self.avatars_dir):
            try:
                os.makedirs(self.avatars_dir, exist_ok=True)
            except PermissionError:
                print("⚠️ Permission denied when creating avatars directory. Using /tmp/avatars instead.")
                self.avatars_dir = "/tmp/avatars"
                os.makedirs(self.avatars_dir, exist_ok=True)
        
        # Directory for storing generated videos - use /tmp on Digital Ocean
        self.videos_dir = os.getenv("OUTPUT_DIR", "generated_videos")
        if not os.path.exists(self.videos_dir):
            try:
                os.makedirs(self.videos_dir, exist_ok=True)
            except PermissionError:
                print("⚠️ Permission denied when creating videos directory. Using /tmp/generated_videos instead.")
                self.videos_dir = "/tmp/generated_videos"
                os.makedirs(self.videos_dir, exist_ok=True)
        
        # Directory for storing avatar images - use /tmp on Digital Ocean
        self.images_dir = os.getenv("IMAGE_DIR", "avatar_images")
        if not os.path.exists(self.images_dir):
            try:
                os.makedirs(self.images_dir, exist_ok=True)
            except PermissionError:
                print("⚠️ Permission denied when creating images directory. Using /tmp/avatar_images instead.")
                self.images_dir = "/tmp/avatar_images"
                os.makedirs(self.images_dir, exist_ok=True)
        
        # End initialization DEBUG marker
        print("===========================================================")
        
        # Create a job storage directory for tracking job status
        self.job_dir = os.path.expanduser("~/sync_jobs")
        try:
            os.makedirs(self.job_dir, exist_ok=True)
        except:
            # Fall back to /tmp if home directory isn't writable
            self.job_dir = "/tmp/sync_jobs"
            os.makedirs(self.job_dir, exist_ok=True)
        
        # Job tracking
        self.jobs_dir = os.path.join(self.job_dir, "sync_jobs")
        os.makedirs(self.jobs_dir, exist_ok=True)
        
        # Define local avatars with metadata using relative paths
        self.avatars = {
            "Sexy News Anchor": {
                "image": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3.png",
                "video": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4",
                "style": "Professional yet alluring",
                "personality": "Confident and engaging",
                "description": "A charismatic news anchor who delivers content with style and charm."
            }
        }
        
        # Verify avatar files exist
        self._verify_avatar_files()

    def _verify_avatar_files(self):
        """Verify that all avatar files exist.
        Skips validation for URLs. Only validates local files."""
        missing_files = []
        
        # Check only local files, completely skip remote URLs
        for avatar_name, avatar_info in self.avatars.items():
            image_url = avatar_info.get("image")
            video_url = avatar_info.get("video")
            
            # Skip URL validation entirely - we trust they exist
            if image_url and image_url.startswith(("http://", "https://")):
                # For URLs, we'll just check that they're properly formatted
                print(f"🔍 Skipping validation for remote image URL: {image_url}")
                continue
                    
            if video_url and video_url.startswith(("http://", "https://")):
                # For URLs, we'll just check that they're properly formatted
                print(f"🔍 Skipping validation for remote video URL: {video_url}")
                continue
                
            # Only check local files
            if image_url and not image_url.startswith(("http://", "https://")):
                if not os.path.exists(image_url):
                    missing_files.append(image_url)
                    
            if video_url and not video_url.startswith(("http://", "https://")):
                if not os.path.exists(video_url):
                    missing_files.append(video_url)
        
        # If any local files are missing, raise an error
        if missing_files:
            print(f"⚠️ Missing avatar files: {', '.join(missing_files)}")
            print(f"Project root: {os.path.dirname(self.job_dir)}")
            # Instead of raising an error, just print a warning
            print("⚠️ Will attempt to continue with remote URLs only")

    def get_available_avatars(self) -> list:
        """Get list of available avatars."""
        return list(self.avatars.keys())

    def get_avatar_info(self, avatar_name: str) -> dict:
        """Get information about a specific avatar."""
        return self.avatars.get(avatar_name)

    def _save_job_info(self, job_id: str, data: dict) -> None:
        """Save job information to a JSON file."""
        job_file = os.path.join(self.jobs_dir, f"{job_id}.json")
        with open(job_file, "w") as f:
            json.dump({
                "id": job_id,
                "created_at": datetime.now().isoformat(),
                "last_checked": datetime.now().isoformat(),
                "status": data.get("status", "PENDING"),
                "data": data
            }, f, indent=2)
            
    def _update_job_info(self, job_id: str, data: dict) -> None:
        """Update job information in the JSON file."""
        job_file = os.path.join(self.jobs_dir, f"{job_id}.json")
        if os.path.exists(job_file):
            with open(job_file, "r") as f:
                job_info = json.load(f)
                
            job_info["last_checked"] = datetime.now().isoformat()
            job_info["status"] = data.get("status", job_info["status"])
            job_info["data"] = data
            
            with open(job_file, "w") as f:
                json.dump(job_info, f, indent=2)
                
    def list_saved_jobs(self) -> list:
        """List all saved jobs."""
        jobs = []
        for file in os.listdir(self.jobs_dir):
            if file.endswith(".json"):
                job_file = os.path.join(self.jobs_dir, file)
                with open(job_file, "r") as f:
                    job_info = json.load(f)
                    jobs.append(job_info)
        return jobs
        
    def check_job_status(self, job_id: str) -> dict:
        """Check the status of a job."""
        try:
            response = requests.get(
                f"{self.base_url}/generate/{job_id}",
                headers=self.headers
            )
            response.raise_for_status()
            status_data = response.json()
            
            # Update job info
            self._update_job_info(job_id, status_data)
            
            return status_data
        except Exception as e:
            st.error(f"❌ Job status check failed: {str(e)}")
            return {"status": "ERROR", "error": str(e)}

    def generate_video(self, audio_file=None, avatar_name=None, settings=None, 
                      poll_for_completion=False, poll_interval=15, indefinite_polling=False, 
                      max_attempts=20, audio_url=None, video_url=None):
        """Generate a lip-synced avatar video
        
        Args:
            audio_file: Path to local audio file
            avatar_name: Name of avatar (from available avatars dir)
            settings: VideoSettings object
            poll_for_completion: Whether to wait for job completion
            poll_interval: Seconds between status checks
            indefinite_polling: Whether to poll indefinitely
            max_attempts: Maximum number of polling attempts
            audio_url: Direct URL to audio file (overrides audio_file if provided)
            video_url: Direct URL to video file (overrides avatar_name if provided)
            
        Returns:
            VideoResult object with video URL and status
        """
        try:
            print("===========================================================")
            print(f"🚀 DEBUG: Starting generate_video method with parameters:")
            print(f"🚀 DEBUG: audio_file = {audio_file}")
            print(f"🚀 DEBUG: avatar_name = {avatar_name}")
            print(f"🚀 DEBUG: poll_for_completion = {poll_for_completion}")
            print(f"🚀 DEBUG: poll_interval = {poll_interval}")
            print(f"🚀 DEBUG: indefinite_polling = {indefinite_polling}")
            print(f"🚀 DEBUG: max_attempts = {max_attempts}")
            print(f"🚀 DEBUG: audio_url = {audio_url}")
            print("===========================================================")
            
            # Use provided video URL or get from avatar
            if video_url:
                avatar_video_url = video_url
            elif avatar_name:
                avatar_info = self.get_avatar_info(avatar_name)
                avatar_video_url = avatar_info.get("video")
            else:
                # Use first available avatar
                avatars = self.get_available_avatars()
                if not avatars:
                    return VideoResult(job_id="error", status="FAILED", error="No avatars available")
                avatar_info = self.get_avatar_info(avatars[0])
                avatar_video_url = avatar_info.get("video")
                
            # Ensure we have a valid video URL
            if not avatar_video_url:
                # Fallback to a default avatar if none specified
                default_avatar_url = "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4"
                print(f"⚠️ No valid avatar video URL found. Using default: {default_avatar_url}")
                avatar_video_url = default_avatar_url
                
            print(f"🚀 DEBUG: Using avatar video URL: {avatar_video_url}")
            
            # Determine audio source - URL or local file
            final_audio_url = None
            if audio_url:
                # Use provided audio URL directly
                final_audio_url = audio_url
                print(f"🚀 DEBUG: Using provided audio URL: {final_audio_url}")
            elif audio_file and os.path.exists(audio_file):
                # Upload local file to S3
                try:
                    from audio_generator import upload_file_to_s3
                    final_audio_url = upload_file_to_s3(
                        file_path=audio_file,
                        s3_key=os.path.basename(audio_file)
                    )
                    print(f"✅ Uploaded audio to S3: {final_audio_url}")
                except Exception as e:
                    error_msg = f"Failed to upload audio to S3: {str(e)}"
                    print(f"❌ {error_msg}")
                    return VideoResult(job_id="error", status="FAILED", error=error_msg)
            else:
                error_msg = "No valid audio source provided (need either audio_url or valid audio_file)"
                print(f"❌ {error_msg}")
                return VideoResult(job_id="error", status="FAILED", error=error_msg)
                
            # Generate the video
            print("===========================================================")
            print(f"🚀 DEBUG: About to start video generation")
            print(f"🚀 DEBUG: Using audio URL: {final_audio_url}")
            print(f"🚀 DEBUG: Using video URL: {avatar_video_url}")
            print("===========================================================")
            
            print(f"🚀 DEBUG: About to call _start_generation method")
            # Start generation
            generation_result = self._start_generation(final_audio_url, avatar_video_url, settings)
            
            # Handle case where API request failed and returned None
            if generation_result is None:
                error_msg = "API request to Sync.so failed. Check logs for details."
                print(f"❌ {error_msg}")
                # Create a failed result with a generic job_id
                return VideoResult(
                    job_id="api_error",
                    status="FAILED",
                    error=error_msg
                )
            
            # Extract job ID
            job_id = generation_result.get('id') or generation_result.get('job_id')
            if not job_id:
                error_msg = "No job ID returned from API"
                print(f"❌ {error_msg}")
                return VideoResult(job_id="error", status="FAILED", error=error_msg)
                
            print(f"🚀 DEBUG: Job ID extracted: {job_id}")
            
            # Build result object
            result = VideoResult(
                job_id=job_id,
                status=generation_result.get('status', 'SUBMITTED')
            )
            
            # Save job info
            self._save_job_info(job_id, generation_result)
            
            # Poll for completion if requested
            if poll_for_completion:
                print(f"🚀 DEBUG: Starting polling with indefinite_polling={indefinite_polling}")
                # Use the public method to poll for completion
                poll_result = self._poll_generation_status(
                    job_id=job_id,
                    max_attempts=max_attempts,
                    poll_interval=poll_interval,
                    indefinite_polling=indefinite_polling
                )
                
                # Update result with polling result if it returned something
                if poll_result:
                    result.status = poll_result.get('status', result.status)
                    result.error = poll_result.get('error')
                    
                    # If completed, set output URL
                    if poll_result.get('status') == 'COMPLETED':
                        result.video_url = self.get_output_url(job_id)
                        result.s3_video_url = poll_result.get('s3_video_url')
                else:
                    # Handle case where polling returned None
                    result.status = "POLLING_FAILED"
                    result.error = "Polling for job status failed. Please check logs."
            
            return result
            
        except Exception as e:
            import traceback
            error_msg = f"Error in generate_video: {str(e)}\n{traceback.format_exc()}"
            print(f"❌ {error_msg}")
            return VideoResult(job_id="error", status="FAILED", error=error_msg)

    def _start_generation(self, audio_url, video_url, settings=None):
        """Start a generation job with the Sync.so API."""
        try:
            # Check the MIME type of the audio file
            import requests
            
            # Try to import streamlit for UI, but don't fail if it's not available
            try:
                import streamlit as st
                has_streamlit = True
            except ImportError:
                has_streamlit = False
                print("Streamlit not available, running in console mode")
            
            # Default MIME types based on file extensions
            audio_content_type = "audio/mpeg"  # Default for most audio files
            video_content_type = "video/mp4"   # Default for MP4 videos
            
            # Properly encode URLs with special characters
            if audio_url and "'" in audio_url or " " in audio_url or "%" not in audio_url:
                original_audio_url = audio_url
                # Only encode if not already encoded
                if "%" not in audio_url:
                    parsed_url = urllib.parse.urlparse(audio_url)
                    path = urllib.parse.quote(parsed_url.path)
                    # Reconstruct URL with encoded path
                    encoded_url = urllib.parse.urlunparse(
                        (parsed_url.scheme, parsed_url.netloc, path, 
                         parsed_url.params, parsed_url.query, parsed_url.fragment)
                    )
                    audio_url = encoded_url
                    print(f"⚠️ URL contains special characters, encoding path: {original_audio_url} -> {audio_url}")
            
            # Also encode video URL if needed
            if video_url and ("'" in video_url or " " in video_url) and "%" not in video_url:
                original_video_url = video_url
                parsed_url = urllib.parse.urlparse(video_url)
                path = urllib.parse.quote(parsed_url.path)
                # Reconstruct URL with encoded path
                encoded_url = urllib.parse.urlunparse(
                    (parsed_url.scheme, parsed_url.netloc, path, 
                     parsed_url.params, parsed_url.query, parsed_url.fragment)
                )
                video_url = encoded_url
                print(f"⚠️ URL contains special characters, encoding path: {original_video_url} -> {video_url}")
            
            # Try to get the actual content type for audio_url from headers
            try:
                print(f"🔍 Checking audio file MIME type: {audio_url}")
                audio_head = requests.head(audio_url, allow_redirects=True)
                if audio_head.status_code == 200 and "Content-Type" in audio_head.headers:
                    detected_content_type = audio_head.headers["Content-Type"]
                    print(f"📄 Audio Content-Type from HEAD: {detected_content_type}")
                    
                    # Only use if it's a valid audio type
                    if "audio/" in detected_content_type:
                        audio_content_type = detected_content_type
                    # Handle common case where S3 returns application/xml for MP3 files
                    elif detected_content_type == "application/xml" and audio_url.lower().endswith('.mp3'):
                        print("⚠️ S3 returned application/xml for an MP3 file, using audio/mpeg instead")
                        audio_content_type = "audio/mpeg"
            except Exception as e:
                print(f"⚠️ Could not determine audio content type from headers: {str(e)}")
                # Determine from file extension as fallback
                if audio_url.lower().endswith('.mp3'):
                    audio_content_type = "audio/mpeg"
                elif audio_url.lower().endswith('.wav'):
                    audio_content_type = "audio/wav"
                elif audio_url.lower().endswith('.ogg'):
                    audio_content_type = "audio/ogg"
            
            print(f"✅ Using detected MIME type: {audio_content_type}")
            
            # Also check video MIME type if needed
            if video_url:
                try:
                    video_head = requests.head(video_url, allow_redirects=True)
                    if video_head.status_code == 200 and "Content-Type" in video_head.headers:
                        detected_content_type = video_head.headers["Content-Type"]
                        if "video/" in detected_content_type:
                            video_content_type = detected_content_type
                except:
                    # Fallback to extension
                    if video_url.lower().endswith('.mp4'):
                        video_content_type = "video/mp4"
            
            # Default settings
            if not settings:
                settings = VideoSettings()
                
            # Create request payload
            payload = {
                "model": settings.model,
                "input": [
                    {
                        "type": "video",
                        "url": video_url,
                        "content_type": video_content_type
                    },
                    {
                        "type": "audio",
                        "url": audio_url,
                        "content_type": audio_content_type
                    }
                ],
                "options": {
                    "output_format": settings.output_format,
                    "sync_mode": "bounce",
                    "fps": 25,
                    "output_resolution": [
                        settings.width,
                        settings.height
                    ],
                    "active_speaker": True
                }
            }
            
            # Pretty print the request payload for console debugging
            import json
            print(f"📊 Request Payload:")
            print(json.dumps(payload, indent=2))
            
            # Show API request details in Streamlit UI if available
            if has_streamlit:
                st.subheader("🔄 Sync.so API Request")
                st.info("Sending request to Sync.so API for lip-sync video generation...")
                
                with st.expander("📤 API Request Details", expanded=False):
                    st.write("**Endpoint:** `https://api.sync.so/v2/generate`")
                    st.write("**Video URL:**")
                    st.code(video_url)
                    st.write("**Audio URL:**")
                    st.code(audio_url)
                    st.write("**Full Request:**")
                    st.json(payload)
            
            print(f"🔄 Sending API request to Sync.so...")
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=payload
            )
            
            # Always log response status
            print(f"📡 Response Status: {response.status_code}")
            
            # Try to raise for HTTP errors
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                # Handle HTTP errors, but consider 201 Created a success
                if e.response.status_code == 201:
                    print(f"✅ Job created with status 201 Created")
                    try:
                        response_json = e.response.json()
                        # Extract job ID
                        job_id = response_json.get("job_id") or response_json.get("id")
                        if job_id:
                            print(f"✅ Job created successfully! Job ID: {job_id}")
                            if has_streamlit:
                                st.success(f"✅ Job created successfully! Job ID: `{job_id}`")
                            # Add the job_id field if it's not there but id is
                            if "job_id" not in response_json and "id" in response_json:
                                response_json["job_id"] = response_json["id"]
                            return response_json
                    except Exception as json_error:
                        print(f"Error parsing 201 response: {json_error}")
                
                print(f"❌ HTTP Error: {e}")
                print(f"Error details: {e.response.text}")
                
                # Show error in UI if available
                if has_streamlit:
                    st.error(f"API Error: {e}")
                    st.error(f"Details: {e.response.text}")
                return None
            
            # Parse response
            response_json = response.json()
            
            # Log the response for debugging
            print(f"🔄 API Response:")
            print(json.dumps(response_json, indent=2))
            
            # Show response in UI if available
            if has_streamlit:
                st.subheader("🔄 Sync.so API Response")
                with st.expander("📥 API Response Details", expanded=True):
                    st.json(response_json)
            
            # Check if job ID exists (try both "job_id" and "id" fields)
            job_id = response_json.get("job_id") or response_json.get("id")
            if job_id:
                print(f"✅ Job created successfully! Job ID: {job_id}")
                if has_streamlit:
                    st.success(f"✅ Job created successfully! Job ID: `{job_id}`")
                # Add the job_id field if it's not there but id is
                if "job_id" not in response_json and "id" in response_json:
                    response_json["job_id"] = response_json["id"]
            else:
                print(f"⚠️ Warning: Response doesn't contain job_id or id field: {response_json}")
                if has_streamlit:
                    st.warning("⚠️ Warning: Response doesn't contain job_id or id field")
            
            return response_json
        except Exception as e:
            print(f"❌ Generation start failed: {str(e)}")
            try:
                import streamlit as st
                st.error(f"❌ Generation start failed: {str(e)}")
            except ImportError:
                # If streamlit isn't available, just continue
                pass
            return None

    def _poll_generation_status(self, job_id: str, max_attempts: int = 30, poll_interval: int = 10,
                             indefinite_polling: bool = False) -> dict:
        """Poll for video generation status.
        
        Args:
            job_id: Job ID to poll
            max_attempts: Maximum number of polling attempts
            poll_interval: Seconds between polling attempts
            indefinite_polling: Whether to poll indefinitely
            
        Returns:
            Dict with job status information
        """
        try:
            print(f"Job polling started for job ID: {job_id}")
            # Create a default result in case of any errors during polling
            default_result = {
                "job_id": job_id,
                "status": "POLLING_ERROR",
                "error": "Failed to get job status"
            }
            
            if indefinite_polling:
                print(f"Will poll indefinitely until job completes")
            else:
                print(f"Will poll for {max_attempts} attempts ({max_attempts * poll_interval} seconds)")
            
            attempts = 0
            
            # Create a container for status messages if in streamlit
            try:
                import streamlit as st
                status_container = st.empty()
            except (ImportError, RuntimeError):
                status_container = None
            
            # Polling loop
            while True:
                attempts += 1
                
                # Update UI if available
                if status_container:
                    status_container.info(f"⏳ Checking job status (attempt {attempts}/{max_attempts if not indefinite_polling else 'unlimited'})...")
                
                # Define a helper function to update logs with consistent formatting
                def update_log(message):
                    print(message)
                    if status_container:
                        status_container.info(message)
                
                try:
                    # Get job status
                    print(f"Poll {attempts}: Status Code", end=" ")
                    status_response = requests.get(
                        f"{self.base_url}/generate/{job_id}",
                        headers=self.headers
                    )
                    print(status_response.status_code)
                    
                    # Check if response is successful
                    if status_response.status_code == 200:
                        # Parse response
                        status_data = status_response.json()
                        
                        # Save job status
                        self._save_job_info(job_id, status_data)
                        
                        # Get job status
                        current_status = status_data.get("status", "UNKNOWN").upper()
                        update_log(f"Job {job_id}: Status = {current_status}, Attempt {attempts}")
                        
                        # Check if job is completed or failed
                        if current_status == "COMPLETED":
                            output_url = status_data.get("outputUrl")
                            update_log(f"✅ Job completed! Video URL: {output_url}")
                            
                            # Download video and upload to S3
                            try:
                                # Download video from Sync.so
                                update_log(f"⬇️ Downloading video from Sync.so...")
                                video_response = requests.get(output_url)
                                if video_response.status_code == 200:
                                    # Create videos directory if it doesn't exist
                                    os.makedirs("generated_videos", exist_ok=True)
                                    
                                    # Save video locally
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    local_video_path = f"generated_videos/sync_video_{timestamp}.mp4"
                                    with open(local_video_path, "wb") as f:
                                        f.write(video_response.content)
                                    
                                    update_log(f"✅ Video downloaded to {local_video_path}")
                                    
                                    # Upload to S3
                                    try:
                                        # Get S3 credentials from environment
                                        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
                                        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                                        s3_bucket = os.getenv("AWS_S3_BUCKET", "vectorverseevolve")
                                        s3_region = os.getenv("AWS_S3_REGION", "us-west-2")
                                        
                                        if aws_access_key and aws_secret_key:
                                            update_log(f"🚀 Uploading video to S3...")
                                            
                                            s3_client = boto3.client('s3', 
                                                                  region_name=s3_region)
                                            
                                            # Extract filename from path
                                            filename = os.path.basename(local_video_path)
                                            
                                            # Upload with proper content type
                                            s3_client.upload_file(
                                                local_video_path, 
                                                s3_bucket, 
                                                filename,
                                                ExtraArgs={'ContentType': 'video/mp4'}
                                            )
                                            
                                            # Generate S3 URL
                                            s3_video_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{filename}"
                                            
                                            update_log(f"✅ Video uploaded to S3: {s3_video_url}")
                                            
                                            # Update job info with S3 URL
                                            status_data["s3_video_url"] = s3_video_url
                                            self._save_job_info(job_id, status_data)
                                            
                                            # Flag for Streamlit to reset state on next run
                                            try:
                                                import streamlit as st
                                                if hasattr(st, 'session_state'):
                                                    st.session_state.needs_reset = True
                                                    update_log("🔄 Flagged session state for reset after job completion")
                                            except (ImportError, AttributeError, RuntimeError):
                                                # Not in a Streamlit context or other error
                                                pass
                                        else:
                                            update_log(f"⚠️ AWS credentials not found. Skipping S3 upload.")
                                    except Exception as s3_error:
                                        update_log(f"⚠️ Error uploading to S3: {str(s3_error)}")
                                else:
                                    update_log(f"⚠️ Error downloading video: Status code {video_response.status_code}")
                            except Exception as download_error:
                                update_log(f"⚠️ Error downloading/processing video: {str(download_error)}")
                            
                            # Return completed status
                            return status_data
                        
                        elif current_status in ["FAILED", "REJECTED", "ERROR"]:
                            error_message = status_data.get("error", "Unknown error")
                            update_log(f"❌ Job failed: {error_message}")
                            return status_data
                        
                        # Continue polling for pending/processing
                        else:
                            # Check if we've reached max attempts
                            if not indefinite_polling and attempts >= max_attempts:
                                update_log(f"⚠️ Maximum polling attempts reached ({max_attempts}). Job is still processing.")
                                if status_container:
                                    status_container.warning(f"⚠️ Maximum polling attempts reached. Check job status later.")
                                
                                # Create a result with polling timeout status
                                timeout_result = status_data.copy()
                                timeout_result["status"] = "POLLING_TIMEOUT"
                                timeout_result["error"] = f"Polling timeout after {max_attempts} attempts"
                                return timeout_result
                            
                            # Wait before next poll
                            update_log(f"⏳ Waiting for {poll_interval} seconds before next check...")
                            time.sleep(poll_interval)
                    else:
                        # Handle API error
                        update_log(f"❌ Error checking job status: API returned {status_response.status_code}")
                        
                        # Try to parse error
                        try:
                            error_data = status_response.json()
                            error_message = error_data.get("message", "Unknown API error")
                        except:
                            error_message = status_response.text
                        
                        # Update default result with specific error
                        default_result["error"] = f"API error: {error_message}"
                        
                        # Check if we've reached max attempts
                        if not indefinite_polling and attempts >= max_attempts:
                            update_log(f"⚠️ Maximum polling attempts reached with API errors")
                            return default_result
                        
                        # Wait before next poll
                        update_log(f"⏳ Waiting for {poll_interval} seconds before next check...")
                        time.sleep(poll_interval)
                    
                except Exception as e:
                    update_log(f"❌ Error polling job status: {str(e)}")
                    if status_container:
                        status_container.error(f"❌ Error during polling: {str(e)}")
                    
                    # Check if we've reached max attempts
                    if not indefinite_polling and attempts >= max_attempts:
                        update_log(f"⚠️ Maximum polling attempts reached with errors")
                        # Set error in default result
                        default_result["error"] = f"Polling error: {str(e)}"
                        return default_result
                    
                    # Wait before next poll
                    time.sleep(poll_interval)
        
        except Exception as e:
            print(f"⚠️ Critical error in polling function: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Create an error result that includes the job_id
            error_result = {
                "job_id": job_id,
                "status": "POLLING_ERROR",
                "error": f"Critical polling error: {str(e)}"
            }
            
            return error_result

    def _poll_job_status(self, job_id: str, polling_interval: int = 10, max_attempts: int = 30, indefinite: bool = False) -> dict:
        """Poll the job status until completion, failure, or timeout."""
        # Try to import streamlit for UI, but don't fail if it's not available
        try:
            import streamlit as st
            has_streamlit = True
        except ImportError:
            has_streamlit = False
            print(f"Polling for job status: {job_id}")
        
        attempts = 0
        
        # Add a status container in Streamlit UI for debugging if available
        if has_streamlit:
            st.subheader("🔄 Job Status Monitoring")
            status_container = st.empty()
            status_container.info(f"Starting to poll job status for job: {job_id}")
            
            debug_container = st.container()
            with debug_container:
                st.write("**Debug Log:**")
                log_area = st.empty()
            
            log_messages = []
        
        def update_log(message):
            print(message)  # Always print to console for terminal logs
            if has_streamlit:
                log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
                log_area.code("\n".join(log_messages), language="bash")
        
        update_log(f"Job polling started for job ID: {job_id}")
        if indefinite:
            update_log("Polling indefinitely until job completes")
        else:
            update_log(f"Will poll for {max_attempts} attempts ({max_attempts * polling_interval} seconds)")
        
        while indefinite or attempts < max_attempts:
            try:
                # IMPORTANT: Fix the API endpoint - use /generate/ not /generation/
                response = requests.get(
                    f"{self.base_url}/generate/{job_id}",
                    headers=self.headers
                )
                
                # Show status code
                update_log(f"Poll {attempts+1}: Status Code {response.status_code}")
                
                # Handle non-200 responses properly
                if response.status_code != 200:
                    update_log(f"Error: {response.status_code} - {response.text}")
                    if response.status_code == 404:
                        update_log("404 Not Found. Check if job ID is correct.")
                    
                    # Display error in UI
                    status_container.error(f"API Error: {response.status_code} {response.reason}")
                    
                    # If unauthorized or not found, no point continuing
                    if response.status_code in [401, 403, 404]:
                        update_log("Critical error, stopping polling")
                        break
                else:
                    job_info = response.json()
                    
                    # Update saved job info
                    self._save_job_status(job_id, job_info)
                    
                    # Log status
                    status = job_info.get("status", "UNKNOWN")
                    update_log(f"Job {job_id}: Status = {status}, Attempt {attempts + 1}")
                    status_container.info(f"Job status: **{status}** (Poll {attempts+1})")
                    
                    # Check if job is done
                    if status == "COMPLETED":
                        output_url = job_info.get("outputUrl")
                        if output_url:
                            update_log(f"✅ Job completed! Video URL: {output_url}")
                            status_container.success(f"Video generation complete!")
                            
                            # Download video and upload to S3
                            try:
                                # Download video from Sync.so
                                update_log(f"⬇️ Downloading video from Sync.so...")
                                video_response = requests.get(output_url)
                                if video_response.status_code == 200:
                                    # Create videos directory if it doesn't exist
                                    os.makedirs("generated_videos", exist_ok=True)
                                    
                                    # Save video locally
                                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    local_video_path = f"generated_videos/sync_video_{timestamp}.mp4"
                                    with open(local_video_path, "wb") as f:
                                        f.write(video_response.content)
                                    
                                    update_log(f"✅ Video downloaded to {local_video_path}")
                                    
                                    # Upload to S3
                                    try:
                                        # Get S3 credentials from environment
                                        aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
                                        aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                                        s3_bucket = os.getenv("AWS_S3_BUCKET", "vectorverseevolve")
                                        s3_region = os.getenv("AWS_S3_REGION", "us-west-2")
                                        
                                        if aws_access_key and aws_secret_key:
                                            update_log(f"🚀 Uploading video to S3...")
                                            
                                            s3_client = boto3.client('s3', 
                                                                  region_name=s3_region)
                                            
                                            # Extract filename from path
                                            filename = os.path.basename(local_video_path)
                                            
                                            # Upload with proper content type
                                            s3_client.upload_file(
                                                local_video_path, 
                                                s3_bucket, 
                                                filename,
                                                ExtraArgs={'ContentType': 'video/mp4'}
                                            )
                                            
                                            # Generate S3 URL
                                            s3_video_url = f"https://{s3_bucket}.s3.{s3_region}.amazonaws.com/{filename}"
                                            
                                            update_log(f"✅ Video uploaded to S3: {s3_video_url}")
                                            
                                            # Update job info with S3 URL
                                            status_data["s3_video_url"] = s3_video_url
                                            self._save_job_info(job_id, status_data)
                                            
                                            # Flag for Streamlit to reset state on next run
                                            try:
                                                import streamlit as st
                                                if hasattr(st, 'session_state'):
                                                    st.session_state.needs_reset = True
                                                    update_log("🔄 Flagged session state for reset after job completion")
                                            except (ImportError, AttributeError, RuntimeError):
                                                # Not in a Streamlit context or other error
                                                pass
                                        else:
                                            update_log(f"⚠️ AWS credentials not found. Skipping S3 upload.")
                                    except Exception as e:
                                        update_log(f"⚠️ Error uploading video to S3: {str(e)}")
                                        # Continue even if S3 upload fails
                                else:
                                    update_log(f"⚠️ Failed to download video: Status code {video_response.status_code}")
                            except Exception as e:
                                update_log(f"⚠️ Error downloading video: {str(e)}")
                        else:
                            update_log("⚠️ Job completed but no output URL found.")
                        
                        return job_info
                    elif status in ["FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                        update_log(f"❌ Job failed! Status: {status}")
                        update_log(f"Error details: {job_info.get('error', 'No error details')}")
                        status_container.error(f"❌ Job failed: {status}")
                        return job_info
                
                # Wait before next poll
                update_log(f"⏳ Waiting for {polling_interval} seconds before next check...")
                time.sleep(polling_interval)
                attempts += 1
                
            except Exception as e:
                update_log(f"❌ Error polling job status: {str(e)}")
                status_container.error(f"❌ Error during polling: {str(e)}")
                time.sleep(polling_interval)
                attempts += 1
        
        update_log(f"⚠️ Maximum polling attempts reached ({max_attempts}). Job is still processing.")
        status_container.warning(f"⚠️ Maximum polling attempts reached. Check job status later.")
        return {"job_id": job_id, "status": "POLLING_TIMEOUT"}

    def get_avatar_video(self, avatar_name: str) -> str:
        """Get the video URL for the specified avatar.
        
        Args:
            avatar_name: Name of the avatar
            
        Returns:
            str: URL to the avatar video
            
        Raises:
            ValueError: If avatar not found
        """
        avatar_info = self.avatars.get(avatar_name)
        if not avatar_info:
            raise ValueError(f"Avatar '{avatar_name}' not found")
            
        video_url = avatar_info.get("video")
        if not video_url:
            raise ValueError(f"Video URL not found for avatar '{avatar_name}'")
            
        return video_url 

    def _save_job_status(self, job_id: str, job_info: dict) -> None:
        """Save job status to disk.
        
        Args:
            job_id: Job ID
            job_info: Job information dictionary
        """
        try:
            # Create jobs directory if it doesn't exist
            os.makedirs(self.jobs_dir, exist_ok=True)
            
            # Add timestamp for when the status was last checked
            job_info["last_checked"] = datetime.now().isoformat()
            
            # Write job info to file
            job_file = os.path.join(self.jobs_dir, f"{job_id}.json")
            with open(job_file, "w") as f:
                json.dump(job_info, f, indent=2)
                
            print(f"✅ Job status saved to {job_file}")
        except Exception as e:
            print(f"⚠️ Error saving job status: {str(e)}")
            # Continue even if saving fails 

    def get_output_url(self, job_id: str) -> str:
        """Get the output URL for a completed job."""
        try:
            # First check if we have the URL saved locally
            job_file = os.path.join(self.jobs_dir, f"{job_id}.json")
            if os.path.exists(job_file):
                with open(job_file, "r") as f:
                    job_info = json.load(f)
                    
                    # First try to get S3 URL (our own backup)
                    if job_info.get("s3_video_url"):
                        return job_info["s3_video_url"]
                    
                    # Then try the API output URL
                    outputUrl = job_info.get("data", {}).get("outputUrl")
                    if outputUrl:
                        return outputUrl
                
            # If not found locally, check with the API
            response = requests.get(
                f"{self.base_url}/generate/{job_id}",
                headers=self.headers
            )
            
            if response.status_code == 200:
                job_data = response.json()
                if job_data.get("status") == "COMPLETED" and job_data.get("outputUrl"):
                    return job_data["outputUrl"]
            
            return None
        except Exception as e:
            print(f"❌ Error getting output URL: {str(e)}")
            return None

    def is_job_completed(self, job_id):
        """Check if a job is already completed and return video details if it is.
        
        Args:
            job_id: Job ID to check
            
        Returns:
            VideoResult object if the job is completed, None otherwise
        """
        try:
            # Check both local storage and API
            job_file = os.path.join(self.jobs_dir, f"{job_id}.json")
            job_info = None
            
            if os.path.exists(job_file):
                with open(job_file, "r") as f:
                    job_info = json.load(f)
            
            # If we don't have the job info locally, check the API
            if not job_info:
                response = requests.get(
                    f"{self.base_url}/generate/{job_id}",
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    job_info = response.json()
                    # Save to local storage
                    self._save_job_info(job_id, job_info)
            
            # If we have job info and it's completed, return a VideoResult
            if job_info and job_info.get("status") == "COMPLETED":
                video_url = job_info.get("data", {}).get("outputUrl") or job_info.get("outputUrl")
                s3_video_url = job_info.get("s3_video_url")
                
                if video_url:
                    return VideoResult(
                        job_id=job_id,
                        status="COMPLETED",
                        video_url=video_url,
                        s3_video_url=s3_video_url
                    )
            
            # If the job exists but is not completed, return its current status
            if job_info:
                return VideoResult(
                    job_id=job_id,
                    status=job_info.get("status", "UNKNOWN"),
                    error=job_info.get("error")
                )
                
            return None
        except Exception as e:
            print(f"❌ Error checking job completion: {str(e)}")
            return None 