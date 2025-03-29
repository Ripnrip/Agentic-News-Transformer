"""Simple test script for Sync.so API with direct URLs."""
import os
import json
import requests
import time

def test_sync_api():
    """Test Sync.so API with direct S3 URLs."""
    print("🧪 Testing Sync.so API with direct S3 URLs...")
    
    # Get API key from environment
    api_key = os.getenv("SYNC_SO_API_KEY")
    if not api_key:
        print("❌ Error: SYNC_SO_API_KEY not found in environment variables")
        return False
    
    # Configure API
    base_url = "https://api.sync.so/v2"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Set up URLs
    audio_url = "https://vectorverseevolve.s3.us-west-2.amazonaws.com/News_Script_20250329_033235.mp3"
    video_url = "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4"
    
    print(f"🔊 Using audio URL: {audio_url}")
    print(f"🎬 Using video URL: {video_url}")
    
    try:
        # Prepare data for generation
        data = {
            "model": "lipsync-1.9.0-beta",
            "input": [
                {
                    "type": "video",
                    "url": video_url
                },
                {
                    "type": "audio",
                    "url": audio_url
                }
            ],
            "options": {
                "output_format": "mp4",
                "sync_mode": "bounce",
                "fps": 25,
                "output_resolution": [640, 1138],  # Original aspect ratio close to 9:16 (portrait)
                "active_speaker": True
            }
        }
        
        print("\n📡 Request data:")
        print(json.dumps(data, indent=2))
        
        # Start generation
        print("\n🚀 Starting generation...")
        response = requests.post(
            f"{base_url}/generate",
            headers=headers,
            json=data
        )
        
        print(f"📊 Response status: {response.status_code}")
        if response.status_code != 201:
            print(f"❌ Generation failed: {response.text}")
            return False
        
        response_data = response.json()
        print("\n📄 Response data:")
        print(json.dumps(response_data, indent=2))
        
        # Get job ID
        job_id = response_data.get("id")
        if not job_id:
            print("❌ No job ID in response")
            return False
        
        print(f"\n✅ Job started successfully with ID: {job_id}")
        
        # Poll for status a few times
        for i in range(3):
            print(f"\n🔄 Checking status (attempt {i+1})...")
            status_response = requests.get(
                f"{base_url}/generate/{job_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code} - {status_response.text}")
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"📊 Current status: {status}")
            
            if status == "COMPLETED":
                print("🎉 Job completed!")
                print(f"🔗 Video URL: {status_data.get('outputUrl')}")
                return True
            
            time.sleep(10)  # Wait 10 seconds between checks
        
        print("\n⏳ Job is still processing. You can check status later with this ID.")
        print(f"📝 Job ID: {job_id}")
        return True
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    test_sync_api() 