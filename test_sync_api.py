"""Test script for Sync.so API functionality."""
import os
import requests
import streamlit as st
import time

def test_sync_api():
    """Test Sync.so API connectivity and basic functionality."""
    print("🔍 Testing Sync.so API connection...")
    
    # Check API key
    api_key = os.getenv("SYNC_SO_API_KEY")
    if not api_key:
        print("❌ Error: SYNC_SO_API_KEY not found in environment variables")
        return False
        
    # API configuration
    base_url = "https://api.sync.so/v2"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    try:
        # Step 1: Testing direct file upload (this might not be supported)
        # According to docs, Sync.so needs URLs, not direct file uploads
        
        # Prepare test files
        test_video = "dependencies/example_input/videos/hoe_3_30.mp4"
        if not os.path.exists(test_video):
            print(f"❌ Error: Test video not found at {test_video}")
            return False
        
        # Create a test audio file if it doesn't exist
        test_audio = "generated_audio/test_audio.mp3"
        if not os.path.exists(test_audio):
            os.makedirs("generated_audio", exist_ok=True)
            # Create a small test MP3 file (1 second of silence)
            with open(test_audio, "wb") as f:
                f.write(b"\x00" * 32000)  # 1 second of silence
        
        # For testing purposes, we'll use public example URLs from the Sync.so docs
        print("\n📤 Using example URLs from Sync.so documentation...")
        video_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortvid-03a10044-7741-4cfc-816a-5bccd392d1ee.mp4"
        audio_url = "https://synchlabs-public.s3.us-west-2.amazonaws.com/david_demo_shortaud-27623a4f-edab-4c6a-8383-871b18961a4a.wav"
        
        # Test: Start a test generation
        print("\n🎬 Test 1: Starting test generation...")
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
                "output_resolution": [1280, 720],
                "active_speaker": True
            }
        }
        
        print("📄 Request payload:")
        print(data)
        
        response = requests.post(
            f"{base_url}/generate",
            headers=headers,
            json=data
        )
        
        print(f"🔄 Response status: {response.status_code}")
        print(f"🔄 Response content: {response.text}")
        
        if response.status_code not in [200, 201]:
            print(f"❌ Generation start failed: {response.status_code} - {response.text}")
            return False
        
        response_data = response.json()
        job_id = response_data.get("id")
        if not job_id:
            print("❌ No job ID in response")
            return False
            
        print("✅ Generation started successfully!")
        print(f"📋 Job ID: {job_id}")
        print(f"📋 Initial status: {response_data.get('status')}")
        
        # Test: Check job status
        print("\n🔄 Test 2: Checking job status...")
        
        # Poll for status a few times to demonstrate
        for i in range(3):
            status_response = requests.get(
                f"{base_url}/generate/{job_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code} - {status_response.text}")
                return False
            
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"✅ Status check {i+1}: {status}")
            
            if status in ["COMPLETED", "FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                break
                
            time.sleep(5)  # Wait 5 seconds between checks
        
        print("\n✨ API connection tests passed!")
        print("Note: Full video generation may still be in progress. Check dashboard for full results.")
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    test_sync_api() 