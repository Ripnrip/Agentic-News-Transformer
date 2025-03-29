"""Test script for ElevenLabs audio generation with S3 uploading."""
import os
import sys
from audio_generator import AudioGenerationAgent, AudioRequest
from dotenv import load_dotenv
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

def main():
    """Generate a test audio file and upload to S3."""
    # Load environment variables
    load_dotenv()
    
    # Check for required env vars
    required_envs = ["ELEVENLABS_API_KEY", "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"]
    missing_envs = [env for env in required_envs if not os.getenv(env)]
    
    if missing_envs:
        print(f"❌ Error: Missing environment variables: {', '.join(missing_envs)}")
        print("Please set these variables in your .env file or environment")
        sys.exit(1)
    
    # Create test script
    test_script = """
    This is a test of the Eleven Labs audio generation with automatic S3 uploading.
    If you're hearing this, it means the integration is working correctly.
    The generated audio file should be automatically uploaded to S3 and accessible via a public URL.
    """
    
    print("🎤 Initializing Audio Generation Agent...")
    audio_agent = AudioGenerationAgent()
    
    # Configure the request
    request = AudioRequest(
        text=test_script,
        title="S3_Upload_Test",
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice ID
        output_dir="generated_audio",
        upload_to_s3=True,
        s3_bucket="vectorverseevolve",
        s3_region="us-west-2"
    )
    
    print("🎵 Generating audio with ElevenLabs and uploading to S3...")
    result = audio_agent.generate_audio_content(request)
    
    if result:
        print("✅ Audio generation successful!")
        print(f"📄 Local file path: {result.audio_file}")
        
        if result.audio_url:
            print("🚀 S3 upload successful!")
            print(f"🔗 Public URL: {result.audio_url}")
            
            # Test URL accessibility
            print("🔍 Testing URL accessibility...")
            import requests
            response = requests.head(result.audio_url)
            if response.status_code == 200:
                print("✅ URL is accessible!")
            else:
                print(f"❌ URL check failed. Status code: {response.status_code}")
        else:
            print("❌ S3 upload failed or URL not returned")
    else:
        print("❌ Audio generation failed")

if __name__ == "__main__":
    main() 