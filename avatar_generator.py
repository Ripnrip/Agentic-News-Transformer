"""Agent for generating lip-synced avatar videos using local avatars and Sync.so API."""
import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import requests
import streamlit as st
import boto3
import json

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
    
    def __init__(self):
        """Initialize the avatar generation agent."""
        self.sync_api_key = os.getenv("SYNC_SO_API_KEY")
        
        # Debug: Check if API key was loaded
        print("\n===========================================================")
        print("🔑 DEBUG: Initializing AvatarGenerationAgent")
        
        if not self.sync_api_key:
            print("❌ ERROR: SYNC_SO_API_KEY environment variable not set!")
            raise ValueError("SYNC_SO_API_KEY environment variable not set")
        else:
            # Show first/last few characters of the API key for debugging
            key_length = len(self.sync_api_key)
            masked_key = f"{self.sync_api_key[:4]}...{self.sync_api_key[-4:]}" if key_length > 8 else "too_short"
            print(f"✅ SYNC_SO_API_KEY loaded: {masked_key} (length: {key_length})")
        
        print("===========================================================\n")
        
        # Get the project root directory (where this file is located)
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define paths relative to project root
        self.dependencies_dir = os.path.join(self.project_root, "dependencies")
        self.example_input_dir = os.path.join(self.dependencies_dir, "example_input")
        self.videos_dir = os.path.join(self.example_input_dir, "videos")
        self.images_dir = os.path.join(self.example_input_dir, "images")
        
        # Ensure directories exist
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.images_dir, exist_ok=True)
        
        # Job tracking
        self.jobs_dir = os.path.join(self.project_root, "sync_jobs")
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
        
        # API endpoints
        self.base_url = "https://api.sync.so/v2"
        self.headers = {
            "x-api-key": self.sync_api_key,
            "Content-Type": "application/json"
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
            print(f"Project root: {os.path.dirname(self.project_root)}")
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

    def generate_video(self, audio_file: str, avatar_name: str, settings: VideoSettings = None, 
                     poll_for_completion: bool = True, poll_interval: int = 10, 
                     indefinite_polling: bool = False, max_attempts: int = 30,
                     audio_url: str = None) -> VideoResult:
        """Generate lip-synced video using Sync.so API."""
        try:
            print("\n\n===========================================================")
            print("🚀 DEBUG: Starting generate_video method with parameters:")
            print(f"🚀 DEBUG: audio_file = {audio_file}")
            print(f"🚀 DEBUG: avatar_name = {avatar_name}")
            print(f"🚀 DEBUG: poll_for_completion = {poll_for_completion}")
            print(f"🚀 DEBUG: poll_interval = {poll_interval}")
            print(f"🚀 DEBUG: indefinite_polling = {indefinite_polling}")
            print(f"🚀 DEBUG: max_attempts = {max_attempts}")
            print(f"🚀 DEBUG: audio_url = {audio_url}")
            print("===========================================================")
            
            # Step 1: Get avatar URLs from the registry
            avatar_video_url = self.get_avatar_video(avatar_name)
            print(f"🚀 DEBUG: Using avatar video URL: {avatar_video_url}")
            
            # For audio, we need to use a public URL 
            # Since we don't have direct upload support, we'll use a hosted solution
            if audio_url:
                print(f"🚀 DEBUG: Using provided audio URL: {audio_url}")
                st.write(f"✅ Using audio URL: {audio_url}")
            else:
                st.error("⚠️ Audio file must be hosted on a public URL to work with Sync.so")
                st.info("""
                ### Upload Steps:
                1. Upload your audio file to AWS S3 or similar service
                2. Make it publicly accessible
                3. Copy the public URL here
                
                Sync.so cannot access files from your local machine.
                """)
                
                base_filename = os.path.basename(audio_file)
                suggested_name = f"News_Script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                audio_url = st.text_input(
                    "Enter public URL for your audio file:",
                    value=f"https://vectorverseevolve.s3.us-west-2.amazonaws.com/{suggested_name}",
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
            
            st.write(f"✅ Using video URL: {avatar_video_url}")
            
            # Step 2: Start video generation
            print("\n\n===========================================================")
            print("🚀 DEBUG: About to start video generation")
            print(f"🚀 DEBUG: Using audio URL: {audio_url}")
            print(f"🚀 DEBUG: Using video URL: {avatar_video_url}")
            print("===========================================================")
            
            print("🚀 DEBUG: About to call _start_generation method")
            response = self._start_generation(
                audio_url=audio_url,
                video_url=avatar_video_url,
                settings=settings
            )
            
            print(f"🚀 DEBUG: _start_generation returned: {response}")
            
            if not response:
                print("🚀 DEBUG: No valid response received")
                return VideoResult(
                    job_id="error",
                    status="FAILED",
                    error="Failed to start video generation. No response received."
                )
            
            # Extract job ID
            job_id = response.get("job_id") or response.get("id")
            if not job_id:
                print("🚀 DEBUG: No valid job_id received")
                return VideoResult(
                    job_id="error",
                    status="FAILED",
                    error="Failed to start video generation. Response doesn't contain job ID."
                )
                
            print(f"🚀 DEBUG: Job ID extracted: {job_id}")
            
            # Save initial job status
            self._save_job_status(job_id, response)
            
            # Poll for job completion if requested
            if poll_for_completion:
                print(f"🚀 DEBUG: Starting polling with indefinite_polling={indefinite_polling}")
                job_info = self._poll_job_status(
                    job_id=job_id,
                    polling_interval=poll_interval,
                    max_attempts=max_attempts,
                    indefinite=indefinite_polling
                )
                
                status = job_info.get("status", "UNKNOWN")
                output_url = job_info.get("outputUrl")
                s3_video_url = job_info.get("s3_video_url")
                
                return VideoResult(
                    job_id=job_id,
                    status=status,
                    video_url=output_url,
                    s3_video_url=s3_video_url,
                    error=job_info.get("error")
                )
            else:
                # Return immediately without polling
                return VideoResult(
                    job_id=job_id,
                    status=response.get("status", "PENDING")
                )
                
        except Exception as e:
            print(f"❌ Error generating avatar video: {str(e)}")
            import traceback
            traceback.print_exc()
            
            return VideoResult(
                job_id="error",
                status="FAILED",
                error=str(e)
            )

    def _upload_file(self, file_path: str, content_type: str) -> dict:
        """Upload a file to Sync.so.
        Note: Direct file upload may not be supported by Sync.so API.
        This is a placeholder for potential future support."""
        st.warning("⚠️ Direct file upload to Sync.so may not be supported. Using pre-hosted URLs is recommended.")
        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                response = requests.post(
                    f"{self.base_url}/upload",
                    headers={"x-api-key": self.sync_api_key},
                    files=files
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            st.error(f"❌ Upload failed: {str(e)}")
            # If upload fails, we'll create a mock response with a local file URL
            # This is just for testing purposes
            return {"url": f"file://{file_path}"}

    def _start_generation(self, audio_url: str, video_url: str, settings: VideoSettings = None) -> dict:
        """Start video generation job."""
        try:
            print(f"\n🎥 SYNC.SO API REQUEST:")
            print(f"🔗 API Endpoint: {self.base_url}/generate")
            
            # Clean up URLs to ensure proper encoding
            import urllib.parse
            
            # Fix double-encoded URLs if present
            if "%25" in audio_url:
                print("🔍 Detected potentially double-encoded URL, fixing...")
                audio_url = audio_url.replace("%2520", "%20")
                audio_url = audio_url.replace("%252F", "%2F")
                print(f"🔧 Fixed audio URL: {audio_url}")
            
            data = {
                "model": settings.model if settings else "lipsync-1.9.0-beta",
                "input": [
                    {
                        "type": "video",
                        "url": video_url,
                        "content_type": "video/mp4"  # Explicitly specify MIME type
                    },
                    {
                        "type": "audio",
                        "url": audio_url,
                        "content_type": "audio/mpeg"  # Explicitly specify MIME type for mp3
                    }
                ],
                "options": {
                    "output_format": settings.output_format if settings else "mp4",
                    "sync_mode": "bounce",
                    "fps": 25,
                    "output_resolution": [480, 854],  # 9:16 aspect ratio for portrait videos
                    "active_speaker": True
                }
            }
            
            # Pretty print the request payload for console debugging
            import json
            print(f"📊 Request Payload:")
            print(json.dumps(data, indent=2))
            
            # Show API request details in Streamlit UI
            st.subheader("🔄 Sync.so API Request")
            st.info("Sending request to Sync.so API for lip-sync video generation...")
            
            with st.expander("📤 API Request Details", expanded=False):
                st.write("**Endpoint:** `https://api.sync.so/v2/generate`")
                st.write("**Video URL:**")
                st.code(video_url)
                st.write("**Audio URL:**")
                st.code(audio_url)
                st.write("**Full Request:**")
                st.json(data)
            
            print(f"🔄 Sending API request to Sync.so...")
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=data
            )
            
            # Always log response status
            print(f"📡 Response Status: {response.status_code}")
            
            # Try to raise for HTTP errors
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                print(f"❌ HTTP Error: {e}")
                print(f"Error details: {response.text}")
                
                # Show error in UI
                st.error(f"API Error: {e}")
                st.error(f"Details: {response.text}")
                return None
            
            # Parse response
            response_json = response.json()
            
            # Log the response for debugging
            print(f"🔄 API Response:")
            print(json.dumps(response_json, indent=2))
            
            # Show response in UI
            st.subheader("🔄 Sync.so API Response")
            with st.expander("📥 API Response Details", expanded=True):
                st.json(response_json)
            
            # Check if job ID exists (try both "job_id" and "id" fields)
            job_id = response_json.get("job_id") or response_json.get("id")
            if job_id:
                print(f"✅ Job created successfully! Job ID: {job_id}")
                st.success(f"✅ Job created successfully! Job ID: `{job_id}`")
                # Add the job_id field if it's not there but id is
                if "job_id" not in response_json and "id" in response_json:
                    response_json["job_id"] = response_json["id"]
            else:
                print(f"⚠️ Warning: Response doesn't contain job_id or id field: {response_json}")
                st.warning("⚠️ Warning: Response doesn't contain job_id or id field")
            
            return response_json
        except Exception as e:
            print(f"❌ Generation start failed: {str(e)}")
            st.error(f"❌ Generation start failed: {str(e)}")
            return None

    def _poll_generation_status(self, job_id: str, max_attempts: int = 30, poll_interval: int = 10,
                               indefinite_polling: bool = False) -> dict:
        """Poll for video generation status.
        
        Args:
            job_id: The job ID to check
            max_attempts: Maximum number of polling attempts (ignored if indefinite_polling=True)
            poll_interval: Interval between polls in seconds
            indefinite_polling: If True, will poll indefinitely until completion or failure
        """
        attempts = 0
        progress_bar = st.progress(0)
        status_text = st.empty()
        poll_info = st.empty()
        
        # Show info about polling duration
        if indefinite_polling:
            poll_info.info("🔄 Polling indefinitely until job completes. This could take a long time.")
        else:
            poll_info.info(f"🔄 Will poll for up to {max_attempts * poll_interval} seconds (~{max_attempts * poll_interval / 60:.1f} minutes).")
        
        while indefinite_polling or attempts < max_attempts:
            try:
                response = requests.get(
                    f"{self.base_url}/generate/{job_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                status_data = response.json()
                
                # Update job info
                self._update_job_info(job_id, status_data)
                
                # Update progress
                if indefinite_polling:
                    # For indefinite polling, use a pulsing progress bar
                    progress = (attempts % 10) / 10
                    progress_bar.progress(progress)
                else:
                    progress = min((attempts + 1) / max_attempts, 1.0)
                    progress_bar.progress(progress)
                
                # Get status from the response
                status = status_data.get("status", "PROCESSING")
                current_time = datetime.now().strftime("%H:%M:%S")
                if indefinite_polling:
                    status_text.write(f"⏳ Status: {status} (Poll #{attempts+1}, Time: {current_time})")
                else:
                    status_text.write(f"⏳ Status: {status} ({int(progress * 100)}%, Time: {current_time})")
                
                # Log full response for debugging
                with st.expander("Response Details"):
                    st.code(str(status_data), language="json")
                
                if status == "COMPLETED":
                    progress_bar.progress(1.0)
                    poll_info.success(f"✅ Generation completed after {attempts+1} polls ({(attempts+1) * poll_interval} seconds)!")
                    status_text.success("✅ Generation completed!")
                    return {
                        "video_url": status_data.get("outputUrl"), 
                        "duration": status_data.get("outputDuration", 30)
                    }
                elif status in ["FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                    error_msg = status_data.get("error", "Unknown error")
                    poll_info.error(f"❌ Generation failed after {attempts+1} polls: {error_msg}")
                    status_text.error(f"❌ Generation failed: {error_msg}")
                    return None
                
                time.sleep(poll_interval)
                attempts += 1
                
            except Exception as e:
                status_text.error(f"❌ Status check failed: {str(e)}")
                return None
        
        if indefinite_polling:
            # This should never happen with indefinite polling
            status_text.error("❌ Unexpected polling termination.")
        else:
            status_text.warning(f"⚠️ Reached maximum polling attempts ({max_attempts}). The job is still running and you can check its status later.")
        
        return None

    def _poll_job_status(self, job_id: str, polling_interval: int = 10, max_attempts: int = 30, indefinite: bool = False) -> dict:
        """Poll the job status until completion, failure, or timeout."""
        attempts = 0
        
        # Add a status container in Streamlit UI for debugging
        st.subheader("🔄 Job Status Monitoring")
        status_container = st.empty()
        status_container.info(f"Starting to poll job status for job: {job_id}")
        
        debug_container = st.container()
        with debug_container:
            st.write("**Debug Log:**")
            log_area = st.empty()
            
        log_messages = []
        
        def update_log(message):
            log_messages.append(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
            log_area.code("\n".join(log_messages), language="bash")
            print(message)  # Also print to console for terminal logs
        
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
                                            status_container.success(f"Video also backed up to S3!")
                                            
                                            # Add S3 URL to job info
                                            job_info["s3_video_url"] = s3_video_url
                                            self._save_job_status(job_id, job_info)
                                        else:
                                            update_log("⚠️ AWS credentials not found. Skipping S3 upload.")
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