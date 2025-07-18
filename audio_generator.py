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
        elif file_path.lower().endswith('.m4a'):
            content_type = 'audio/mp4'
        elif file_path.lower().endswith('.mp4'):
            content_type = 'video/mp4'
        elif file_path.lower().endswith('.json'):
            content_type = 'application/json'
        elif file_path.lower().endswith('.txt'):
            content_type = 'text/plain'
        elif file_path.lower().endswith('.srt'):
            content_type = 'text/plain'
        
        # Upload the file
        with open(file_path, 'rb') as f:
            s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=f,
                ContentType=content_type
            )
        
        # Return the public URL
        return f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
        
    except Exception as e:
        print(f"Error uploading to S3: {e}")
        return None

class AudioRequest(BaseModel):
    """Request model for audio generation."""
    text: str = Field(description="Text to convert to speech")
    title: str = Field(description="Title for the audio file")
    voice: str = Field(default="nova", description="OpenAI voice (alloy, echo, fable, onyx, nova, shimmer)")
    output_dir: str = Field(default="generated_audio", description="Output directory for audio files")
    upload_to_s3: bool = Field(default=False, description="Whether to upload the audio to S3")
    s3_bucket: str = Field(default="vectorverseevolve", description="S3 bucket to upload to")
    s3_region: str = Field(default="us-west-2", description="AWS region of the S3 bucket")

class SubtitleOptions(BaseModel):
    """Options for subtitle generation."""
    format: str = Field(default="srt", description="Subtitle format (srt, vtt)")
    words_per_segment: int = Field(default=10, description="Words per subtitle segment")
    max_segment_length: int = Field(default=7, description="Maximum seconds per segment")

class AudioResult(BaseModel):
    """Result model for audio generation."""
    audio_file: str = Field(description="Path to the generated audio file")
    script_file: str = Field(description="Path to the script file")
    srt_file: str = Field(description="Path to the SRT subtitle file")
    script_text: str = Field(description="The script text")
    duration: float = Field(description="Estimated duration in seconds")
    s3_url: str = Field(default="", description="Public URL for the audio file (if uploaded to S3)")

class AudioGenerationAgent:
    """Agent for generating audio content using OpenAI TTS."""
    
    def __init__(self):
        """Initialize the audio generation agent."""
        # Set up OpenAI client
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Create the agent
        self.agent = Agent(
            "openai:gpt-4",  # Using OpenAI for script processing
            deps_type=dict,  # Audio request will be passed as dependency
            result_type=AudioResult,
            system_prompt="Generate audio content and subtitles from text using OpenAI TTS."
        )

    def upload_to_s3(self, file_path: str, bucket: str, region: str) -> str:
        """Upload a file to AWS S3 and return the public URL."""
        return upload_file_to_s3(file_path, bucket_name=bucket, region=region)

    def generate_audio_content(self, request: AudioRequest) -> AudioResult:
        """Generate audio content from text using OpenAI TTS."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(request.output_dir, exist_ok=True)
            
            # Generate unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Clean title for filename
            safe_title = "".join(c for c in request.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_title = safe_title.replace(' ', '_')
            
            audio_file = os.path.join(request.output_dir, f"{safe_title}_{timestamp}.mp3")
            script_file = os.path.join(request.output_dir, f"{safe_title}_{timestamp}.txt")
            srt_file = os.path.join(request.output_dir, f"{safe_title}_{timestamp}.srt")
            
            # Generate audio using OpenAI TTS
            response = self.openai_client.audio.speech.create(
                model="tts-1",
                voice=request.voice,
                input=request.text,
                response_format="mp3"
            )
            
            # Save audio file
            with open(audio_file, "wb") as f:
                f.write(response.content)
            
            # Save script file
            with open(script_file, "w") as f:
                f.write(request.text)
            
            # Generate and save SRT file
            self._generate_srt(request.text, srt_file)
            
            # Calculate estimated duration (assuming average speaking rate)
            words = len(request.text.split())
            duration = words / 2.5  # Assuming 2.5 words per second
            
            # Create result object
            result = AudioResult(
                audio_file=audio_file,
                script_file=script_file,
                srt_file=srt_file,
                script_text=request.text,
                duration=duration
            )
            
            # Upload to S3 if requested
            if request.upload_to_s3:
                try:
                    # Check for AWS credentials
                    aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
                    aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
                    
                    if not aws_access_key or not aws_secret_key:
                        print("⚠️ Warning: AWS credentials not found. Skipping S3 upload.")
                        print("Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables to enable S3 upload.")
                    else:
                        s3_url = self.upload_to_s3(
                            audio_file, 
                            request.s3_bucket, 
                            request.s3_region
                        )
                        if s3_url:
                            result.s3_url = s3_url
                            print(f"Audio uploaded to S3: {s3_url}")
                except Exception as e:
                    print(f"Error uploading to S3: {str(e)}")
                    # Continue even if S3 upload fails
            
            return result
            
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return AudioResult(
                audio_file="",
                script_file="",
                srt_file="",
                script_text=request.text,
                duration=0,
                s3_url=""
            )

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

# Simple interface function for backward compatibility
def generate_audio_content(article_content: dict, openai_client=None, voice: str = "nova") -> dict:
    """Generate audio from article content using OpenAI TTS."""
    # Extract text content
    text = ""
    if isinstance(article_content, dict):
        if "headline" in article_content:
            text += f"{article_content['headline']}\n\n"
        if "intro" in article_content:
            text += f"{article_content['intro']}\n\n"
        if "body" in article_content:
            text += f"{article_content['body']}\n\n"
        if "conclusion" in article_content:
            text += f"{article_content['conclusion']}"
    else:
        text = str(article_content)
    
    # Create request
    request = AudioRequest(
        text=text,
        title=article_content.get("headline", "Untitled Article") if isinstance(article_content, dict) else "Generated Audio",
        voice=voice
    )
    
    # Generate audio
    agent = AudioGenerationAgent()
    result = agent.generate_audio_content(request)
    
    if result and result.audio_file:
        return result.dict()
    else:
        return {
            "audio_file": "",
            "script_file": "",
            "srt_file": "",
            "script_text": text,
            "duration": 0,
            "s3_url": ""
        }