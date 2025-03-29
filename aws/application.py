"""AWS Elastic Beanstalk wrapper for the Streamlit application."""
import os
import subprocess
import sys

def apply_subprocess_fix():
    """Fix for subprocess calls on AWS Elastic Beanstalk."""
    # Fix Python path for subprocess calls
    os.environ["PATH"] = f"{os.environ.get('PATH', '')}:{sys.executable[:sys.executable.rfind('/')]}"

def run_streamlit():
    """Run the Streamlit application."""
    # Get the port from environment variable or use default
    port = os.environ.get("PORT", 8501)
    
    # Run Streamlit as a subprocess
    cmd = [
        "streamlit", "run", 
        "news_to_avatar.py", 
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.enableCORS", "false",
        "--server.enableXsrfProtection", "false"
    ]
    
    # Execute the command
    subprocess.Popen(cmd)

# Apply fixes for AWS
apply_subprocess_fix()

# Application entry point for AWS Elastic Beanstalk
application = run_streamlit()

# If run directly (for testing)
if __name__ == "__main__":
    run_streamlit() 