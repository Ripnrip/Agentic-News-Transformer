from typing import Dict, List
import os
import uuid
from datetime import datetime, timedelta
import json
from textwrap import dedent
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

class AudioGenerationAgent:
    """Agent for converting blog content to audio and subtitles."""
    
    def __init__(self, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        """Initialize with ElevenLabs configuration."""
        self.voice_id = voice_id
        self.client = ElevenLabs(
            api_key=os.getenv("ELEVENLABS_API_KEY")
        )
        self.voice_settings = VoiceSettings(
            stability=0.0,
            similarity_boost=1.0,
            style=0.0,
            use_speaker_boost=True
        )
    
    def _convert_to_script(self, article: Dict, openai_client) -> str:
        """Convert blog post to conversational script."""
        prompt = dedent(f"""
            Convert this blog post into a natural, conversational news report script.
            Make it engaging like a TV news segment.

            Headline: {article['headline']}
            
            Content:
            {article['intro']}
            
            {article['body']}
            
            {article['conclusion']}
            
            Format as a natural conversation with clear speaker indicators.
            Include brief pauses and emphasis where appropriate.
            Use [PAUSE] to indicate natural breaks.
            
            Keep the technical accuracy but make it more conversational.
        """)
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert news script writer."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        return response.choices[0].message.content
    
    def _generate_audio(self, script: str) -> bytes:
        """Generate audio using ElevenLabs API."""
        response = self.client.text_to_speech.convert(
            voice_id=self.voice_id,
            output_format="mp3_22050_32",
            text=script,
            model_id="eleven_turbo_v2",
            voice_settings=self.voice_settings
        )
        
        # Create a bytes buffer for the audio
        audio_data = bytes()
        for chunk in response:
            if chunk:
                audio_data += chunk
        
        return audio_data
    
    def _create_srt(self, script: str, words_per_segment: int = 24) -> str:
        """Create SRT subtitle file content."""
        lines = script.split('\n')
        segments = []
        current_segment = []
        word_count = 0
        
        for line in lines:
            words = line.split()
            for word in words:
                current_segment.append(word)
                word_count += 1
                
                if word_count >= words_per_segment or '[PAUSE]' in word:
                    segments.append(' '.join(current_segment))
                    current_segment = []
                    word_count = 0
        
        # Add any remaining words
        if current_segment:
            segments.append(' '.join(current_segment))
        
        # Create SRT format with timing
        srt_content = []
        current_time = timedelta(seconds=0)
        for i, segment in enumerate(segments, 1):
            # Estimate duration based on word count (avg 0.4s per word)
            duration = len(segment.split()) * 0.4
            end_time = current_time + timedelta(seconds=duration)
            
            srt_content.append(f"{i}\n{self._format_timecode(current_time)} --> {self._format_timecode(end_time)}\n{segment}\n")
            current_time = end_time
            
        return "\n".join(srt_content)
    
    def _format_timecode(self, td: timedelta) -> str:
        """Format timedelta as SRT timecode."""
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        milliseconds = int(td.microseconds / 1000)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def generate_audio_content(self, article: Dict, openai_client) -> Dict:
        """Generate audio and subtitles from article content."""
        # Create output directory
        output_dir = "generated_audio"
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"{output_dir}/audio_{timestamp}"
        
        # Convert to script
        print("Converting to script...")
        script = self._convert_to_script(article, openai_client)
        
        # Generate audio
        print("Generating audio...")
        audio = self._generate_audio(script)
        
        # Generate SRT
        print("Creating subtitles...")
        srt_content = self._create_srt(script)
        
        # Save files
        audio_file = f"{base_filename}.mp3"
        script_file = f"{base_filename}.txt"
        srt_file = f"{base_filename}.srt"
        
        with open(audio_file, 'wb') as f:
            f.write(audio)
        with open(script_file, 'w') as f:
            f.write(script)
        with open(srt_file, 'w') as f:
            f.write(srt_content)
            
        return {
            "audio_file": audio_file,
            "script_file": script_file,
            "srt_file": srt_file,
            "script": script,
            "duration": len(script.split()) * 0.4  # Estimated duration in seconds
        } 