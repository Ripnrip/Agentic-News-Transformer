from audio_generator import AudioGenerationAgent, AudioRequest

def main():
    # Initialize audio agent
    agent = AudioGenerationAgent()
    
    # Create script
    script = """The cryptocurrency market is evolving rapidly with new innovations aimed at mainstream adoption. Pi Network and FloppyPepe are making waves as potential bridges to everyday crypto use, simplifying access for non-technical users. While Pi Network focuses on mobile mining without draining batteries, FloppyPepe's presale offers a unique meme coin approach to mass adoption. Both aim to solve the complexity barriers that have kept cryptocurrencies from reaching everyday consumers. The crypto landscape continues to mature, and these developments could be crucial steps toward bringing digital currencies into our daily lives."""
    
    # Generate audio
    print("Generating audio and uploading to S3...")
    result = agent.generate_audio_content(
        AudioRequest(
            text=script,
            title="Crypto_Adoption_News",
            upload_to_s3=True
        )
    )
    
    if result and result.audio_url:
        print(f"Audio generated and uploaded to S3: {result.audio_url}")
    else:
        print("Failed to generate audio")

if __name__ == "__main__":
    main() 