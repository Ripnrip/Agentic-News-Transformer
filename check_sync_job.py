"""Script to check the status of a Sync.so job."""
import os
import json
import requests
import sys
import argparse
import time

def check_job_status(job_id, poll=False, poll_interval=30, max_polls=None):
    """Check the status of a Sync.so job.
    
    Args:
        job_id: The ID of the job to check
        poll: Whether to continuously poll until completion
        poll_interval: Seconds between polls
        max_polls: Maximum number of polling attempts (None for indefinite)
    """
    print(f"🔍 Checking status of job {job_id}...")
    
    api_key = os.getenv("SYNC_SO_API_KEY")
    if not api_key:
        print("❌ Error: SYNC_SO_API_KEY not found in environment variables")
        return False
    
    base_url = "https://api.sync.so/v2"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    
    polls = 0
    try:
        while True:
            # If we're polling, show progress
            if poll and polls > 0:
                print(f"\n🔄 Poll attempt #{polls}{f'/{max_polls}' if max_polls else ''}...")
            
            response = requests.get(
                f"{base_url}/generate/{job_id}",
                headers=headers
            )
            
            if response.status_code != 200:
                print(f"❌ Status check failed: {response.status_code} - {response.text}")
                return False
            
            status_data = response.json()
            status = status_data.get("status")
            print(f"📊 Current status: {status} at {time.strftime('%H:%M:%S')}")
            
            # Print full response for the first poll or every 5 polls
            if not poll or polls == 0 or polls % 5 == 0:
                print("\n📄 Full response data:")
                print(json.dumps(status_data, indent=2))
            
            # Check for completion status
            if status == "COMPLETED":
                print("\n🎉 Job completed!")
                print(f"🔗 Video URL: {status_data.get('outputUrl')}")
                if status_data.get('outputUrl'):
                    print("\nView your video at:")
                    print(status_data.get('outputUrl'))
                return True
            elif status in ["FAILED", "REJECTED", "CANCELED", "TIMED_OUT"]:
                print(f"\n❌ Job failed: {status}")
                print(f"Error: {status_data.get('error')}")
                return False
            else:
                print(f"\n⏳ Job is still processing ({status}).")
                
                # If we're not polling or we've reached max polls, return
                if not poll or (max_polls and polls >= max_polls):
                    return True
                
                # Otherwise, wait and poll again
                print(f"Waiting {poll_interval} seconds before next check...")
                time.sleep(poll_interval)
                polls += 1
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check the status of a Sync.so job")
    parser.add_argument("job_id", help="The ID of the job to check")
    parser.add_argument("--poll", "-p", action="store_true", help="Continuously poll until job is complete")
    parser.add_argument("--interval", "-i", type=int, default=30, help="Polling interval in seconds (default: 30)")
    parser.add_argument("--max-polls", "-m", type=int, help="Maximum number of polling attempts (default: indefinite)")
    args = parser.parse_args()
    
    if not args.job_id:
        print("Please provide a job ID to check")
        sys.exit(1)
        
    check_job_status(args.job_id, args.poll, args.interval, args.max_polls) 