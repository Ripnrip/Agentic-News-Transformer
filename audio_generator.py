"""Agent for converting blog content to audio using Pydantic AI."""
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
import uuid
from datetime import datetime
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Define model types
class AudioRequest(BaseModel):
    """Model for audio generation request."""
    text: str
    title: str = "Untitled Content"
    voice_id: str = Field(default="21m00Tcm4TlvDq8ikWAM", description="ElevenLabs voice ID")
    output_dir: str = "generated_audio"

class SubtitleOptions(BaseModel):
    """Model for subtitle generation options."""
    format: str = "srt"  # srt or vtt
    words_per_segment: int = 10
    max_segment_length: int = 4  # in seconds

class AudioResult(BaseModel):
    """Model for audio generation result."""
    audio_file: str
    script_file: str
    srt_file: str
    script: str
    duration: float  # estimated in seconds

# Create the agent
audio_agent = Agent(
    "openai:gpt-4o",
    deps_type=Any,
    result_type=AudioResult,
    system_prompt="Convert blog content to audio and generate subtitles."
)

# Initialize ElevenLabs client
eleven_client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

@audio_agent.tool
def generate_audio_from_text(
    ctx: RunContext[Any],
    request: AudioRequest,
    subtitle_options: Optional[SubtitleOptions] = None
) -> AudioResult:
    """
    Generate audio and subtitles from text content.
    
    Args:
        ctx: Runtime context (not used)
        request: Audio generation parameters
        subtitle_options: Options for subtitle generation
        
    Returns:
        Paths to generated files and metadata
    """
    # Set default subtitle options
    if subtitle_options is None:
        subtitle_options = SubtitleOptions()
    
    # Ensure output directory exists
    os.makedirs(request.output_dir, exist_ok=True)
    
    # Generate unique ID for this audio
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_prefix = f"audio_{timestamp}"
    
    # Create file paths
    audio_file = os.path.join(request.output_dir, f"{file_prefix}.mp3")
    script_file = os.path.join(request.output_dir, f"{file_prefix}.txt")
    srt_file = os.path.join(request.output_dir, f"{file_prefix}.srt")
    
    # Generate voice audio using ElevenLabs
    voice_settings = VoiceSettings(
        stability=0.5,
        similarity_boost=0.75,
        style=0.0,
        use_speaker_boost=True
    )
    
    try:
        # Generate audio
        audio_data = b""
        response = eleven_client.text_to_speech.convert(
            text=request.text,
            voice_id=request.voice_id,
            model_id="eleven_turbo_v2",
            voice_settings=voice_settings,
            output_format="mp3_44100_128"
        )
        
        for chunk in response:
            if chunk:
                audio_data += chunk
        
        # Save audio to file
        with open(audio_file, 'wb') as f:
            f.write(audio_data)
        
        # Save script to file
        with open(script_file, 'w') as f:
            f.write(request.text)
        
        # Generate SRT subtitles
        srt_content = _generate_srt(
            request.text,
            words_per_segment=subtitle_options.words_per_segment,
            max_segment_length=subtitle_options.max_segment_length
        )
        
        # Save SRT to file
        with open(srt_file, 'w') as f:
            f.write(srt_content)
        
        # Estimate duration (rough estimate based on word count)
        estimated_duration = len(request.text.split()) * 0.4  # avg 0.4 seconds per word
        
        return AudioResult(
            audio_file=audio_file,
            script_file=script_file,
            srt_file=srt_file,
            script=request.text,
            duration=estimated_duration
        )
    
    except Exception as e:
        raise RuntimeError(f"Error generating audio: {str(e)}")

def _generate_srt(text: str, words_per_segment: int = 10, max_segment_length: int = 4) -> str:
    """Generate SRT subtitles from text."""
    words = text.split()
    srt_content = ""
    segment_index = 1
    start_time = 0
    
    for i in range(0, len(words), words_per_segment):
        segment_words = words[i:i+words_per_segment]
        segment_text = " ".join(segment_words)
        
        # Calculate timing
        segment_length = min(len(segment_words) * 0.4, max_segment_length)
        end_time = start_time + segment_length
        
        # Format time codes (HH:MM:SS,mmm)
        start_formatted = _format_srt_time(start_time)
        end_formatted = _format_srt_time(end_time)
        
        # Add entry to SRT
        srt_content += f"{segment_index}\n{start_formatted} --> {end_formatted}\n{segment_text}\n\n"
        
        # Update for next segment
        segment_index += 1
        start_time = end_time
    
    return srt_content

def _format_srt_time(seconds: float) -> str:
    """Format seconds as SRT timestamp."""
    hours = int(seconds / 3600)
    minutes = int((seconds % 3600) / 60)
    secs = int(seconds % 60)
    millisecs = int((seconds - int(seconds)) * 1000)
    
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"

# Simple interface function
def generate_audio_content(article_content: Dict[str, Any], voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Dict[str, Any]:
    """Generate audio from article content."""
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
    
    # Create request
    request = AudioRequest(
        text=text,
        title=article_content.get("headline", "Untitled Article"),
        voice_id=voice_id
    )
    
    # Generate audio
    result = audio_agent.run_sync(
        "Generate audio from this content",
        deps=None,
        inputs={"request": request}
    )
    
    if isinstance(result.data, AudioResult):
        return result.data.dict()
    
    raise ValueError("Failed to generate audio") 