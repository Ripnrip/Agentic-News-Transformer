from avatar_generator import AvatarGenerationAgent

def main():
    # Initialize avatar agent
    agent = AvatarGenerationAgent()
    
    # Audio file from previous step
    audio_file = "generated_audio/Crypto_Adoption_News_20250329_085848.mp3"
    audio_url = "https://vectorverseevolve.s3.us-west-2.amazonaws.com/Crypto_Adoption_News_20250329_085848.mp3"
    
    # Generate video
    print("Generating lip-synced video and uploading to S3...")
    result = agent.generate_video(
        audio_file=audio_file,
        audio_url=audio_url,
        avatar_name="Sexy News Anchor",
        poll_for_completion=True,
        indefinite_polling=True
    )
    
    # The result is a VideoResult object, not a dict
    if result and hasattr(result, 's3_video_url'):
        print(f"Video generated and uploaded to S3: {result.s3_video_url}")
    else:
        print(f"Failed to generate video: {result}")

if __name__ == "__main__":
    main() 