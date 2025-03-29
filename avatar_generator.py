"""Agent for generating lip-synced avatar videos using local avatars and Sync.so API."""
import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import requests
import streamlit as st

class VideoSettings(BaseModel):
    """Settings for video generation."""
    model: str = Field(default="lipsync-1.9.0-beta", description="Sync.so model to use")
    output_format: str = Field(default="mp4", description="Output video format")
    resolution: str = Field(default="portrait", description="Video resolution (portrait or landscape)")
    width: int = Field(default=480, description="Output width in pixels")
    height: int = Field(default=854, description="Output height in pixels")

class VideoResult(BaseModel):
    """Result of video generation."""
    video_url: Optional[str] = Field(None, description="URL of the generated video")
    duration: float = Field(default=0, description="Duration of the video in seconds")
    job_id: str = Field(description="Sync.so job ID")
    status: str = Field(default="PENDING", description="Current status of the job")

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
            import json
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
                import json
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
                    import json
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
            print("===========================================================\n\n")
            
            st.write("🎬 Starting video generation process...")
            
            # Get avatar info
            avatar_info = self.avatars.get(avatar_name)
            if not avatar_info:
                raise ValueError(f"Avatar '{avatar_name}' not found")
            
            # For local audio file, we need to get the path but we'll skip the upload
            audio_path = os.path.abspath(audio_file)
            
            # Verify audio file exists
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
            # Use test files from Sync.so or use AWS S3 URLs
            use_test_files = st.checkbox("Use test files from Sync.so documentation", value=False, 
                                        help="Use this for testing the API without hosting your own files")
            
            if use_test_files:
                print("🚀 DEBUG: Using test files")
                st.info("Using example files from Sync.so documentation for testing")
                audio_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortaud-27623a4f-edab-4c6a-8383-871b18961a4a.wav"
                video_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortvid-03a10044-7741-4cfc-816a-5bccd392d1ee.mp4"
                st.write("✅ Using test files")
            else:
                # For avatar video, we already have the URL in avatar_info
                video_url = avatar_info["video"]
                print(f"🚀 DEBUG: Using avatar video URL: {video_url}")
                
                # For audio, we need to use a public URL 
                # Since we don't have direct upload support, we'll use a hosted solution
                if audio_url:
                    print(f"🚀 DEBUG: Using provided audio URL: {audio_url}")
                    st.write(f"✅ Using provided audio URL: {audio_url}")
                else:
                    st.error("⚠️ Audio file must be hosted on a public URL to work with Sync.so")
                    st.info("""
                    ### Upload Steps:
                    1. Upload your audio file to AWS S3 or similar service
                    2. Make it publicly accessible
                    3. Copy the public URL here
                    
                    Sync.so cannot access files from your local machine.
                    """)
                    
                    base_filename = os.path.basename(audio_path)
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
                
                st.write(f"✅ Using video URL: {video_url}")
            
            # Step 2: Start video generation
            print("\n\n===========================================================")
            print("🚀 DEBUG: About to start video generation")
            print(f"🚀 DEBUG: Using audio URL: {audio_url}")
            print(f"🚀 DEBUG: Using video URL: {video_url}")
            print("===========================================================\n\n")
            
            st.write("🎥 Starting lip-sync process...")
            st.write("Audio URL:", audio_url)
            st.write("Video URL:", video_url)
            
            print("🚀 DEBUG: About to call _start_generation method")
            generation_response = self._start_generation(
                audio_url=audio_url,
                video_url=video_url,
                settings=settings
            )
            print(f"🚀 DEBUG: _start_generation returned: {generation_response}")
            
            if not generation_response or not generation_response.get("job_id"):
                print("🚀 DEBUG: No valid response or job_id received")
                raise Exception("Failed to start video generation. Response doesn't contain job ID.")
            
            # Extract ID based on the actual response structure
            job_id = generation_response.get("job_id") or generation_response.get("id")
            print(f"🚀 DEBUG: Job ID extracted: {job_id}")
            st.write(f"✅ Generation job started (ID: {job_id})")
            
            # Save job info
            self._save_job_info(job_id, generation_response)
            
            # Create job info display
            job_info = st.empty()
            job_info.info(f"""
                🎬 **Video Generation Job Started**
                
                - **Job ID:** `{job_id}`
                - **Status:** {generation_response.get('status', 'PENDING')}
                - **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                
                You can check the status later using the job ID.
            """)
            
            # Step 3: Poll for completion if requested
            if poll_for_completion:
                print(f"🚀 DEBUG: Starting polling with indefinite_polling={indefinite_polling}")
                if indefinite_polling:
                    st.write("⏳ Polling indefinitely until job completes...")
                else:
                    st.write(f"⏳ Polling for completion every {poll_interval} seconds (up to {max_attempts} attempts)...")
                
                result = self._poll_generation_status(
                    job_id, 
                    max_attempts=max_attempts,
                    poll_interval=poll_interval,
                    indefinite_polling=indefinite_polling
                )
                
                if result and result.get("video_url"):
                    st.write("✅ Video generation completed!")
                    return VideoResult(
                        video_url=result["video_url"],
                        duration=result.get("duration", 0),
                        job_id=job_id,
                        status="COMPLETED"
                    )
                else:
                    job_info.warning(f"""
                        ⚠️ **Video Generation Not Completed**
                        
                        - **Job ID:** `{job_id}`
                        - **Status:** INCOMPLETE
                        
                        You can check the status later using the job ID.
                    """)
                    return VideoResult(
                        job_id=job_id,
                        status="PROCESSING"
                    )
            else:
                # Return right away with the job ID
                print("🚀 DEBUG: Returning immediately with job ID")
                return VideoResult(
                    job_id=job_id,
                    status=generation_response.get("status", "PENDING")
                )
            
        except Exception as e:
            print(f"🚀 DEBUG ERROR: {str(e)}")
            st.error(f"❌ Error in video generation: {str(e)}")
            raise

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
            
            st.code(str(data), language="json")
            
            print(f"🔄 Sending API request to Sync.so...")
            response = requests.post(
                f"{self.base_url}/generate",
                headers=self.headers,
                json=data
            )
            
            # Always log response status
            print(f"📡 Response Status: {response.status_code}")
            
            # Try to raise for HTTP errors
            response.raise_for_status()
            
            # Parse response
            response_json = response.json()
            
            # Log the response for debugging
            print(f"🔄 API Response:")
            print(json.dumps(response_json, indent=2))
            
            st.write("🔄 API Response:")
            st.code(response.text, language="json")
            
            # Check if job ID exists (try both "job_id" and "id" fields)
            job_id = response_json.get("job_id") or response_json.get("id")
            if job_id:
                print(f"✅ Job created successfully! Job ID: {job_id}")
                # Add the job_id field if it's not there but id is
                if "job_id" not in response_json and "id" in response_json:
                    response_json["job_id"] = response_json["id"]
            else:
                print(f"⚠️ Warning: Response doesn't contain job_id or id field: {response_json}")
            
            return response_json
        except requests.exceptions.HTTPError as e:
            error_msg = f"HTTP Error: {str(e)}"
            print(f"❌ {error_msg}")
            st.error(f"❌ Generation start failed: {error_msg}")
            
            # Try to parse error response
            try:
                error_json = e.response.json()
                print(f"Error details: {json.dumps(error_json, indent=2)}")
                st.error(f"Error details: {error_json}")
            except:
                print("Could not parse error response as JSON")
            
            return None
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