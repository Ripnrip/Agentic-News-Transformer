"""Agent for generating audio content using OpenAI text-to-speech."""
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
import json
import requests
from openai import OpenAI
from datetime import datetime
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
import urllib.parse
import subprocess
import streamlit as st
from typing import Optional, Union

# Add a global upload_file_to_s3 function that can be imported directly
def upload_file_to_s3(file_path, s3_key=None, bucket_name="vectorverseevolve", region="us-west-2"):
    """Upload a file to S3 and return the public URL.
    
    Args:
        file_path: Path to the file to upload
        s3_key: Optional key to use in S3, defaults to file name
        bucket_name: S3 bucket name
        region: AWS region
        
    Returns:
        The URL of the uploaded file or None if upload fails
    """
    try:
        # Create an S3 client
        s3_client = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
        
        # If no S3 key provided, use the filename
        if not s3_key:
            s3_key = os.path.basename(file_path)
        
        # Clean up key (replace spaces with underscores)
        s3_key = s3_key.replace(' ', '_')
        
        # Determine content type based on file extension
        content_type = 'application/octet-stream'  # Default
        if file_path.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif file_path.lower().endswith('.wav'):
            content_type = 'audio/wav'
        elif file_path.lower().endswith('.mp4'):
            content_type = 'video/mp4'
        
        # Set content type - ACL removed for buckets with ACLs disabled
        extra_args = {
            'ContentType': content_type
            # No ACL setting to ensure compatibility with all bucket configurations
        }
        
        # Upload file
        s3_client.upload_file(
            file_path,
            bucket_name,
            s3_key,
            ExtraArgs=extra_args
        )
        
        # Generate URL
        s3_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        print(f"File uploaded to S3: {s3_url}")
        return s3_url
        
    except Exception as e:
        print(f"Error uploading to S3: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

class SubtitleOptions(BaseModel):
    """Options for subtitle generation."""
    format: str = Field(default="srt", description="Subtitle format (srt, vtt)")
    words_per_segment: int = Field(default=10, description="Words per subtitle segment")
    max_segment_length: int = Field(default=7, description="Maximum seconds per segment")

class AudioRequest(BaseModel):
    """Request for generating audio."""
    text: str = Field(..., description="Text to convert to audio")
    title: str = Field(default=None, description="Title for the audio file (will be used as base filename)")
    voice_id: str = Field(default=None, description="Voice name for OpenAI TTS")
    output_dir: str = Field(default="audio", description="Directory to save output files")
    subtitle_options: SubtitleOptions = Field(default=None, description="Options for subtitle generation")
    upload_to_s3: bool = Field(default=True, description="Whether to upload the audio file to S3")
    s3_bucket: str = Field(default="vectorverseevolve", description="S3 bucket to upload to")
    s3_region: str = Field(default="us-west-2", description="AWS region of the S3 bucket")
    s3_folder: str = Field(default=None, description="Optional S3 folder for the audio file")

class AudioResult(BaseModel):
    """Result model for audio generation."""
    audio_file: str = Field(description="Path to the generated audio file")
    script_file: str = Field(description="Path to the script file")
    srt_file: str = Field(description="Path to the SRT subtitle file")
    script_text: str = Field(description="The script text")
    duration: float = Field(description="Estimated duration in seconds")
    audio_url: Optional[str] = Field(default=None, description="Public URL for the audio file (if uploaded to S3)")

    model_config = {
        "arbitrary_types_allowed": True,
    }

class AudioGenerationAgent:
    """Agent for generating audio content."""
    
    def __init__(self):
        """Initialize the audio generation agent."""
        # Initialize OpenAI client for TTS
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # Default female voice for TTS
        self.voice_id = os.getenv("OPENAI_VOICE", "nova")
        print(f"Initializing AudioGenerationAgent with OpenAI voice: {self.voice_id}")
        
        # S3 configuration
        self.s3_region = os.getenv("AWS_S3_REGION", "us-west-2")
        self.s3_bucket = os.getenv("AWS_S3_BUCKET", "vectorverseevolve")
        self.s3_folder = None
        
        # Create the agent
        self.agent = Agent(
            "openai:gpt-4",  # Using OpenAI for script processing
            deps_type=dict,  # Audio request will be passed as dependency
            result_type=AudioResult,
            system_prompt="Generate audio content and subtitles from text."
        )

    def _upload_to_s3(self, file_path, s3_key=None):
        """Upload a file to S3.
        
        Args:
            file_path: Path to the file to upload
            s3_key: The S3 key to use. If None, the filename will be used.
            
        Returns:
            The URL of the uploaded file
        """
        try:
            # Create an S3 client
            print(f"🌐 Creating S3 client with region: {self.s3_region}")
            s3_client = boto3.client(
                's3',
                region_name=self.s3_region,
                aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
            )
            
            # If no S3 key provided, use the filename
            if not s3_key:
                s3_key = os.path.basename(file_path)
            
            # Check if there's a specific folder in the request
            if self.s3_folder:
                s3_key = f"{self.s3_folder}/{s3_key}"
            
            # Upload the file
            print(f"📤 Uploading {file_path} to S3 bucket {self.s3_bucket} with key {s3_key}")
            
            # Add ContentType to ensure proper MIME type
            # Determine content type based on file extension
            content_type = 'audio/mpeg'  # Default for MP3 files
            if file_path.lower().endswith('.wav'):
                content_type = 'audio/wav'
            elif file_path.lower().endswith('.mp3'):
                content_type = 'audio/mpeg'
            
            # Set content type without ACL (bucket has ACLs disabled)
            extra_args = {
                'ContentType': content_type
                # ACL removed to prevent errors with buckets that have ACLs disabled
            }
            
            s3_client.upload_file(
                file_path, 
                self.s3_bucket, 
                s3_key,
                ExtraArgs=extra_args
            )
            
            # Generate the URL
            s3_url = f"https://{self.s3_bucket}.s3.{self.s3_region}.amazonaws.com/{s3_key}"
            print(f"✅ Upload successful. S3 URL: {s3_url}")
            
            return s3_url
        except Exception as e:
            print(f"❌ Error uploading to S3: {str(e)}")
            import traceback
            print(traceback.format_exc())
            return None

    def generate_audio_content(self, request: AudioRequest) -> AudioResult:
        """Generate audio content from text."""
        audio_file = ""
        script_file = ""
        srt_file = ""
        audio_url = ""
        duration = 0.0
        
        try:
            # Create output directory if it doesn't exist
            os.makedirs(request.output_dir, exist_ok=True)
            
            # Create a timestamp for the files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create file paths
            base_filename = f"{request.title}_{timestamp}"
            base_path = os.path.join(request.output_dir, base_filename)
            audio_file = f"{base_path}.mp3"
            script_file = f"{base_path}.txt"
            srt_file = f"{base_path}.srt"
            
            # Save script to text file
            st.write(f"Saving script to {script_file}")
            with open(script_file, 'w') as f:
                f.write(request.text)
                
            # Generate audio using OpenAI TTS
            st.write("Generating audio with OpenAI TTS...")
            audio_bytes = self._generate_audio_with_openai(
                text=request.text,
                voice_id=request.voice_id or self.voice_id
            )
            
            # Save audio to file
            st.write(f"Saving audio to {audio_file}")
            with open(audio_file, 'wb') as f:
                f.write(audio_bytes)
            
            # Get audio duration for subtitles
            duration = self._get_audio_duration(audio_file)
            st.write(f"Audio duration: {duration:.2f} seconds")
            
            # Generate subtitles
            st.write("Generating subtitles...")
            subtitles = self._generate_subtitles(
                text=request.text,
                audio_duration=duration
            )
            
            # Save subtitles to SRT file
            st.write(f"Saving subtitles to {srt_file}")
            with open(srt_file, 'w') as f:
                f.write(subtitles)
            
            # Create result with local paths
            result = AudioResult(
                audio_file=audio_file,
                script_file=script_file,
                srt_file=srt_file,
                script_text=request.text,
                duration=duration,
                audio_url=""
            )
            
            # Upload to S3 if requested
            audio_url = None
            if request.upload_to_s3:
                try:
                    # Use curl for S3 upload instead of the SDK
                    # Create a safe filename for S3 by replacing spaces with underscores
                    original_filename = os.path.basename(audio_file)
                    safe_s3_key = original_filename.replace(' ', '_')
                    
                    st.write(f"Creating safe S3 key: {safe_s3_key}")
                    
                    # Update S3 configuration from request
                    self.s3_bucket = request.s3_bucket
                    self.s3_region = request.s3_region
                    self.s3_folder = request.s3_folder
                    
                    audio_url = self._upload_to_s3(
                        file_path=audio_file,
                        s3_key=safe_s3_key
                    )
                    
                    if not audio_url:
                        st.warning("⚠️ S3 upload failed. Using local file path instead.")
                        audio_url = ""  # Use empty string instead of None
                    else:
                        # Verify the MIME type
                        try:
                            import requests
                            response = requests.head(audio_url, timeout=5)
                            content_type = response.headers.get('Content-Type', '')
                            
                            if 'audio/mpeg' in content_type.lower():
                                st.success(f"✅ Verified correct MIME type: {content_type}")
                            else:
                                st.warning(f"⚠️ Audio file has unexpected MIME type: {content_type}")
                                st.info("Attempting to use it anyway...")
                        except Exception as e:
                            st.warning(f"⚠️ Could not verify MIME type: {str(e)}")
                            
                except Exception as e:
                    st.error(f"❌ S3 upload error: {str(e)}")
                    st.warning("⚠️ Continuing with local file path...")
                    audio_url = ""  # Use empty string instead of None
            else:
                audio_url = ""  # Default to empty string if upload not requested
                
            # Update audio_url in result only if we got a valid URL
            if audio_url:
                result.audio_url = audio_url
                
            return result
            
        except Exception as e:
            st.error(f"❌ Error generating audio: {str(e)}")
            
            # If we've already created some files, return what we have
            if audio_file or script_file or srt_file:
                st.warning("Returning partial results with local files")
                return AudioResult(
                    audio_file=audio_file or f"{request.output_dir}/error.mp3",
                    script_file=script_file or f"{request.output_dir}/error.txt",
                    srt_file=srt_file or f"{request.output_dir}/error.srt",
                    script_text=request.text,
                    duration=duration or 0.0,
                    audio_url=""
                )
            
            # Re-raise the exception if we couldn't create any files
            raise

    def _generate_srt(self, text: str, output_file: str):
        """Generate SRT subtitles from text."""
        try:
            words = text.split()
            segments = []
            current_segment = []
            current_time = 0
            
            for word in words:
                current_segment.append(word)
                if len(current_segment) >= 10:  # Words per segment
                    duration = len(current_segment) / 2.5  # Assuming 2.5 words per second
                    segments.append({
                        "text": " ".join(current_segment),
                        "start": current_time,
                        "end": current_time + duration
                    })
                    current_time += duration
                    current_segment = []
            
            # Add any remaining words
            if current_segment:
                duration = len(current_segment) / 2.5
                segments.append({
                    "text": " ".join(current_segment),
                    "start": current_time,
                    "end": current_time + duration
                })
            
            # Write SRT file
            with open(output_file, "w") as f:
                for i, segment in enumerate(segments, 1):
                    f.write(f"{i}\n")
                    f.write(f"{self._format_srt_time(segment['start'])} --> {self._format_srt_time(segment['end'])}\n")
                    f.write(f"{segment['text']}\n\n")
                    
        except Exception as e:
            print(f"Error generating SRT: {str(e)}")

    def _format_srt_time(self, seconds: float) -> str:
        """Format seconds into SRT timestamp (HH:MM:SS,mmm)."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

    def _generate_audio_with_openai(self, text: str, voice_id: str) -> bytes:
        """Generate audio using OpenAI's text-to-speech API."""
        try:
            response = self.client.audio.speech.create(
                input=text,
                model="tts-1",
                voice=voice_id,
                response_format="mp3",
            )
            return response.content
        except Exception as e:
            st.error(f"OpenAI TTS error: {str(e)}")
            raise
            
    def _get_audio_duration(self, audio_file: str) -> float:
        """Get the duration of an audio file in seconds."""
        try:
            import wave
            import contextlib
            
            # For mp3 files, we'll use a simple approximation based on file size
            # 128kbps MP3 is ~16KB per second
            if audio_file.endswith('.mp3'):
                file_size = os.path.getsize(audio_file)
                return file_size / 16000  # Approximate duration
            
            # For WAV files, we can get precise duration
            elif audio_file.endswith('.wav'):
                with contextlib.closing(wave.open(audio_file, 'r')) as f:
                    frames = f.getnframes()
                    rate = f.getframerate()
                    return frames / float(rate)
            
            # Default fallback - use word count
            else:
                # Read file content
                with open(audio_file.replace('.mp3', '.txt').replace('.wav', '.txt'), 'r') as f:
                    content = f.read()
                
                # Calculate based on average speaking rate (2.5 words per second)
                words = len(content.split())
                return words / 2.5
                
        except Exception as e:
            st.warning(f"Error getting audio duration: {str(e)}")
            # Fallback to a default duration
            return 30.0
            
    def _generate_subtitles(self, text: str, audio_duration: float) -> str:
        """Generate SRT subtitles from text based on audio duration."""
        try:
            words = text.split()
            total_words = len(words)
            
            # If no words, return empty string
            if total_words == 0:
                return ""
                
            # Calculate words per second based on audio duration
            words_per_second = total_words / audio_duration
            
            # Aim for subtitle segments of about 5 seconds each
            words_per_segment = int(words_per_second * 5)
            if words_per_segment < 3:
                words_per_segment = 3  # Minimum 3 words per segment
            elif words_per_segment > 12:
                words_per_segment = 12  # Maximum 12 words per segment
                
            segments = []
            current_segment = []
            current_time = 0
            
            for word in words:
                current_segment.append(word)
                
                if len(current_segment) >= words_per_segment:
                    # Calculate segment duration based on word count
                    segment_word_count = len(current_segment)
                    segment_duration = segment_word_count / words_per_second
                    
                    segments.append({
                        "text": " ".join(current_segment),
                        "start": current_time,
                        "end": current_time + segment_duration
                    })
                    
                    current_time += segment_duration
                    current_segment = []
            
            # Add any remaining words
            if current_segment:
                segment_word_count = len(current_segment)
                segment_duration = segment_word_count / words_per_second
                
                segments.append({
                    "text": " ".join(current_segment),
                    "start": current_time,
                    "end": current_time + segment_duration
                })
            
            # Write SRT format
            srt_content = ""
            for i, segment in enumerate(segments, 1):
                srt_content += f"{i}\n"
                srt_content += f"{self._format_srt_time(segment['start'])} --> {self._format_srt_time(segment['end'])}\n"
                srt_content += f"{segment['text']}\n\n"
                
            return srt_content
                    
        except Exception as e:
            st.warning(f"Error generating subtitles: {str(e)}")
            # Return minimal SRT with the full text
            return f"1\n00:00:00,000 --> 00:{int(audio_duration//60):02d}:{int(audio_duration%60):02d},000\n{text}\n" 