"""Script to generate a new video with proper aspect ratio."""
import os
import json
import requests
import time
import argparse

def generate_fixed_video():
    """Generate a new video with proper aspect ratio."""
    print("🎬 Starting video generation with fixed aspect ratio...")
    
    # Check API key
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
                "output_resolution": [480, 854],  # 9:16 aspect ratio
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
        
        # Poll for status indefinitely
        print("\n⏳ Polling for completion (press Ctrl+C to stop)...")
        
        poll_count = 0
        while True:
            poll_count += 1
            print(f"\n🔄 Checking status (attempt {poll_count})...")
            status_response = requests.get(
                f"{base_url}/generate/{job_id}",
                headers=headers
            )
            
            if status_response.status_code != 200:
                print(f"❌ Status check failed: {status_response.status_code} - {status_response.text}")
                time.sleep(10)
                continue
            
            status_data = status_response.json()
            status = status_data.get("status")
            print(f"📊 Current status: {status}")
            
            if status == "COMPLETED":
                print("🎉 Job completed!")
                output_url = status_data.get("outputUrl")
                print(f"🔗 Video URL: {output_url}")
                
                # Save job information
                with open("fixed_aspect_job.json", "w") as f:
                    json.dump(status_data, f, indent=2)
                
                print(f"\nJob information saved to fixed_aspect_job.json")
                return output_url
            elif status in ["FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                print(f"❌ Job failed with status {status}")
                print(f"Error: {status_data.get('error')}")
                return False
            
            print(f"Waiting 10 seconds before next check...")
            time.sleep(10)
        
    except KeyboardInterrupt:
        print("\n⚠️ Polling stopped by user. You can check the status later with:")
        print(f"python check_sync_job.py {job_id} --poll")
        return job_id
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🎥 Generating new video with fixed aspect ratio...")
    video_url = generate_fixed_video()
    
    if video_url:
        print("\n✅ Success! The video is available at:")
        print(video_url)
    else:
        print("\n❌ Failed to generate video with fixed aspect ratio.") 