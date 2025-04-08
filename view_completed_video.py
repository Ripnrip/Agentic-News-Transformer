"""Script to view completed Sync.so videos."""
import os
import json
import argparse
import webbrowser
import sys

def load_known_jobs():
    """Load all known jobs from the known_jobs.json file."""
    try:
        with open("known_jobs.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ Error: known_jobs.json file not found.")
        return {}
    except json.JSONDecodeError:
        print("❌ Error: known_jobs.json is not a valid JSON file.")
        return {}

def load_job_from_file(job_id):
    """Load a specific job file from the sync_jobs directory."""
    job_file = os.path.join("sync_jobs", f"{job_id}.json")
    try:
        with open(job_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: Job file for {job_id} not found.")
        return None
    except json.JSONDecodeError:
        print(f"❌ Error: Job file for {job_id} is not valid JSON.")
        return None

def get_latest_job():
    """Get the most recently created job from known_jobs.json."""
    jobs = load_known_jobs()
    if not jobs:
        return None
    
    # Sort by created_at date (newest first)
    sorted_jobs = sorted(
        jobs.values(), 
        key=lambda j: j.get("created_at", ""), 
        reverse=True
    )
    
    if sorted_jobs:
        return sorted_jobs[0]
    return None

def view_job(job_id=None, latest=False, with_notes=False):
    """View information about a specific job and open the video if available."""
    if latest:
        job = get_latest_job()
        if not job:
            print("❌ No jobs found in known_jobs.json")
            return False
        job_id = job.get("id")
    elif job_id:
        jobs = load_known_jobs()
        job = jobs.get(job_id)
        if not job:
            job = load_job_from_file(job_id)
    else:
        print("❌ Please provide a job ID or use --latest")
        return False
    
    if not job:
        print(f"❌ Job with ID {job_id} not found")
        return False
    
    # Display job information
    print("\n🎬 Job Information:")
    print(f"ID: {job.get('id')}")
    print(f"Status: {job.get('status')}")
    print(f"Created: {job.get('created_at')}")
    
    if with_notes and "notes" in job:
        print(f"Notes: {job.get('notes')}")
    
    # Get video URL
    video_url = job.get("video_url")
    if not video_url and "data" in job:
        video_url = job.get("data", {}).get("outputUrl")
    
    if not video_url:
        print("❌ No video URL found for this job")
        return False
    
    print(f"Video URL: {video_url}")
    
    # Ask to open in browser
    open_in_browser = input("\n🌐 Open video in browser? (y/n): ").lower() == 'y'
    if open_in_browser:
        print(f"Opening {video_url} in browser...")
        webbrowser.open(video_url)
    
    return True

def list_all_jobs():
    """List all known jobs with their IDs and statuses."""
    jobs = load_known_jobs()
    if not jobs:
        print("❌ No jobs found in known_jobs.json")
        return False
    
    print("\n📋 Known Jobs:")
    # Sort by created_at date (newest first)
    sorted_jobs = sorted(
        jobs.values(), 
        key=lambda j: j.get("created_at", ""), 
        reverse=True
    )
    
    for i, job in enumerate(sorted_jobs):
        job_id = job.get("id", "unknown")
        status = job.get("status", "unknown")
        created = job.get("created_at", "unknown")
        notes = job.get("notes", "")
        
        # Format job ID for better display
        short_id = job_id[:8] + "..." if len(job_id) > 8 else job_id
        
        # Add status emoji
        status_emoji = "✅" if status == "COMPLETED" else "⏳" if status in ["PENDING", "PROCESSING"] else "❌"
        
        print(f"{i+1}. {status_emoji} {short_id} - {status} - {created}")
        if notes:
            print(f"   📝 {notes}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="View completed Sync.so videos")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--job-id", help="The ID of the job to view")
    group.add_argument("--latest", action="store_true", help="View the latest job")
    group.add_argument("--list", action="store_true", help="List all known jobs")
    parser.add_argument("--notes", action="store_true", help="Show job notes if available")
    
    args = parser.parse_args()
    
    if args.list:
        list_all_jobs()
    elif args.latest or args.job_id:
        view_job(args.job_id, args.latest, args.notes)
    else:
        # Default to listing all jobs if no arguments provided
        list_all_jobs()
        
        # Ask the user to select a job
        job_num = input("\nEnter job number to view (or press Enter to exit): ")
        if job_num.strip():
            try:
                job_num = int(job_num)
                jobs = load_known_jobs()
                sorted_jobs = sorted(
                    jobs.values(), 
                    key=lambda j: j.get("created_at", ""), 
                    reverse=True
                )
                
                if 1 <= job_num <= len(sorted_jobs):
                    selected_job = sorted_jobs[job_num - 1]
                    view_job(selected_job.get("id"), False, args.notes)
                else:
                    print("❌ Invalid job number")
            except ValueError:
                print("❌ Please enter a valid number") 