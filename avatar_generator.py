"""Agent for generating lip-synced avatar videos from audio using Pydantic AI."""
import os
import subprocess
from typing import Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# Define model types
class VideoSettings(BaseModel):
    """Settings for video generation."""
    resolution: str = Field(default="full", description="Video resolution (full, half, quarter)")
    enhance_face: bool = Field(default=True, description="Whether to enhance the face")

class VideoResult(BaseModel):
    """Result of video generation."""
    video_path: str = Field(description="Path to the generated video file")
    audio_path: str = Field(description="Path to the input audio file")
    avatar_name: str = Field(description="Name of the avatar used")
    settings: VideoSettings = Field(description="Settings used for generation")

# Create the agent
avatar_agent = Agent(
    "openai:gpt-4o",  # Using OpenAI for reasoning
    deps_type=str,    # Audio file path will be passed as dependency
    result_type=VideoResult,
    system_prompt="Generate lip-synced videos from audio using a predefined avatar."
)

# Set default paths
WAV2LIP_PATH = "Wav2Lip"
CHECKPOINT_PATH = os.path.join(WAV2LIP_PATH, "checkpoints", "wav2lip_gan.pth")
DEFAULT_AVATAR = "default_avatar.mp4"  # Single avatar approach
AVATARS_DIR = "avatars"
OUTPUT_DIR = "generated_videos"

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(AVATARS_DIR, exist_ok=True)

@avatar_agent.tool
def generate_lipsync_video(
    ctx: RunContext[str],
    settings: VideoSettings,
    avatar_name: str = DEFAULT_AVATAR
) -> VideoResult:
    """
    Generate a lip-synced video using Wav2Lip.
    
    Args:
        ctx: Contains the audio file path
        settings: Video generation settings
        avatar_name: Name of avatar file (defaults to the single avatar)
    
    Returns:
        VideoResult with generated video information
    """
    audio_file = ctx.deps  # Audio file path from dependency
    
    # Validate Wav2Lip installation
    if not os.path.exists(WAV2LIP_PATH):
        raise FileNotFoundError(f"Wav2Lip directory not found at {WAV2LIP_PATH}")
    
    if not os.path.exists(CHECKPOINT_PATH):
        raise FileNotFoundError(f"Wav2Lip checkpoint not found at {CHECKPOINT_PATH}")
    
    # Get avatar path
    avatar_path = os.path.join(AVATARS_DIR, avatar_name)
    if not os.path.exists(avatar_path):
        raise FileNotFoundError(f"Avatar template not found: {avatar_path}")
    
    # Create output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{OUTPUT_DIR}/avatar_{timestamp}.mp4"
    
    # Prepare Wav2Lip command
    cmd = [
        "python", f"{WAV2LIP_PATH}/inference.py",
        "--checkpoint_path", CHECKPOINT_PATH,
        "--face", avatar_path,
        "--audio", audio_file,
        "--outfile", output_file,
        "--pads", "0", "0", "0", "0"  # Default padding
    ]
    
    # Add optional arguments
    if settings.resolution == "half":
        cmd.extend(["--resize_factor", "2"])
    elif settings.resolution == "quarter":
        cmd.extend(["--resize_factor", "4"])
        
    if settings.enhance_face:
        cmd.append("--face_enhancement")
    
    # Run Wav2Lip
    try:
        print(f"Running command: {' '.join(cmd)}")
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print(f"Wav2Lip Error: {stderr}")
            raise Exception(f"Wav2Lip failed with error code {process.returncode}")
            
        print(f"Successfully generated video: {output_file}")
        
        # Return structured result
        return VideoResult(
            video_path=output_file,
            audio_path=audio_file,
            avatar_name=avatar_name,
            settings=settings
        )
        
    except Exception as e:
        print(f"Error generating lip-synced video: {str(e)}")
        raise

# Helper function for Streamlit integration
def get_avatar_list() -> List[str]:
    """Get list of available avatars (for UI)."""
    if os.path.exists(AVATARS_DIR):
        return [f for f in os.listdir(AVATARS_DIR) 
                if f.endswith(('.mp4', '.avi', '.mov', '.webm'))]
    return [DEFAULT_AVATAR] if os.path.exists(os.path.join(AVATARS_DIR, DEFAULT_AVATAR)) else []

# Simple function to use in app.py
def generate_video(audio_file: str, resolution: str = "full", enhance_face: bool = True) -> str:
    """
    Generate a video with the default avatar and return the path.
    
    Args:
        audio_file: Path to the audio file
        resolution: Video resolution ("full", "half", "quarter")
        enhance_face: Whether to enhance the face
        
    Returns:
        Path to the generated video
    """
    settings = VideoSettings(resolution=resolution, enhance_face=enhance_face)
    result = avatar_agent.run_sync(
        "Generate lip sync video for the provided audio", 
        deps=audio_file
    )
    
    if isinstance(result.data, VideoResult):
        return result.data.video_path
    
    raise ValueError("Failed to generate video") 