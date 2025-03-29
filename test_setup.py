"""
Test script to verify the project setup.
"""

import os
from dotenv import load_dotenv
from env_validator import validate_conda_env

def test_environment():
    """Test that the environment is set up correctly."""
    load_dotenv()
    
    # Check for required environment variables
    required_vars = [
        "OPENAI_API_KEY",
        "COHERE_API_KEY",
        "NEWS_API_KEY",
        "NEWS_DATA_HUB_KEY",
        "ELEVENLABS_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
            missing_vars.append(var)
    
    if missing_vars:
        print("⚠️ The following environment variables are missing or have default values:")
        for var in missing_vars:
            print(f"  - {var}")
        print("\nPlease update your .env file with the correct API keys.")
    else:
        print("✅ All required environment variables are set.")

def test_imports():
    """Test that all required packages can be imported."""
    try:
        import openai
        import cohere
        import langchain
        import chromadb
        import elevenlabs
        import streamlit
        print("✅ All core packages imported successfully.")
    except ImportError as e:
        print(f"❌ Import error: {str(e)}")

def main():
    # Validate conda environment
    validate_conda_env()
    
    print("=== Testing Agentic Content Transformer Setup ===\n")
    test_environment()
    print()
    test_imports()
    print("\n=== Setup Test Complete ===")

if __name__ == "__main__":
    main() 