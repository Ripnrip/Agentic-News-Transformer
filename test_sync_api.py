#!/usr/bin/env python3
"""
Test script to verify the new Sync.so API key works with the API.
"""
import os
import requests
from dotenv import load_dotenv

def test_sync_api():
    print("🔧 Testing Sync.so API connectivity...")
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = os.getenv('SYNC_SO_API_KEY')
    if not api_key:
        print("❌ No API key found")
        return False
    
    print(f"🔑 Using API key: {api_key[:10]}...{api_key[-10:]}")
    
    # Test API endpoint - try a simple request first
    base_url = "https://api.sync.so/v2"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    # Test with a simple request (this might be a status endpoint or similar)
    try:
        print("📡 Testing API connectivity...")
        
        # Create a minimal test request
        test_data = {
            "model": "lipsync-1.9.0-beta",
            "input": [
                {
                    "type": "video",
                    "url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4",
                    "content_type": "video/mp4"
                },
                {
                    "type": "audio", 
                    "url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/News_Script_20250718_165512.mp3",
                    "content_type": "audio/mpeg"
                }
            ],
            "options": {
                "output_format": "mp4",
                "sync_mode": "bounce",
                "fps": 25,
                "output_resolution": [480, 854],
                "active_speaker": True
            }
        }
        
        print("🔄 Sending test request to Sync.so...")
        response = requests.post(
            f"{base_url}/generate",
            json=test_data,
            headers=headers,
            timeout=30
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API Key is valid and working!")
            response_data = response.json()
            print(f"📄 Response: {response_data}")
            return True
        elif response.status_code == 401:
            print("❌ API Key is invalid or expired")
            print(f"📄 Response: {response.text}")
            return False
        elif response.status_code == 402:
            print("⚠️ API Key is valid but account has insufficient credits")
            print(f"📄 Response: {response.text}")
            return False
        else:
            print(f"⚠️ API returned status {response.status_code}")
            print(f"📄 Response: {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_sync_api()
    if success:
        print("\n🎉 Sync.so API test passed! Ready to generate videos.")
    else:
        print("\n❌ Sync.so API test failed. Please check the API key or account status.")