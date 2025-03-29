"""Agent for generating audio content using ElevenLabs."""
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
import json
import requests
from datetime import datetime

class AudioRequest(BaseModel):
    """Request model for audio generation."""
    text: str = Field(description="Text to convert to speech")
    title: str = Field(description="Title for the audio file")
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="ElevenLabs voice ID")
    output_dir: str = Field(default="generated_audio", description="Output directory for audio files")

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

class AudioGenerationAgent:
    """Agent for generating audio content."""
    
    def __init__(self):
        """Initialize the audio generation agent."""
        # Set up ElevenLabs API key
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY environment variable not set")
        
        # API endpoints
        self.base_url = "https://api.elevenlabs.io/v1"
        
        # Create the agent
        self.agent = Agent(
            "openai:gpt-4",  # Using OpenAI for script processing
            deps_type=dict,  # Audio request will be passed as dependency
            result_type=AudioResult,
            system_prompt="Generate audio content and subtitles from text."
        )

    def generate_audio_content(self, request: AudioRequest) -> AudioResult:
        """Generate audio content from text."""
        try:
            # Create output directory if it doesn't exist
            os.makedirs(request.output_dir, exist_ok=True)
            
            # Generate unique filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_file = os.path.join(request.output_dir, f"{request.title}_{timestamp}.mp3")
            script_file = os.path.join(request.output_dir, f"{request.title}_{timestamp}.txt")
            srt_file = os.path.join(request.output_dir, f"{request.title}_{timestamp}.srt")
            
            # Generate audio using ElevenLabs API
            url = f"{self.base_url}/text-to-speech/{request.voice_id}"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.api_key
            }
            
            data = {
                "text": request.text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True
                }
            }
            
            response = requests.post(url, json=data, headers=headers)
            
            if response.status_code == 200:
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
                
                return AudioResult(
                    audio_file=audio_file,
                    script_file=script_file,
                    srt_file=srt_file,
                    script_text=request.text,
                    duration=duration
                )
            else:
                print(f"ElevenLabs API error: {response.status_code} - {response.text}")
                return None
            
        except Exception as e:
            print(f"Error generating audio: {str(e)}")
            return None

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