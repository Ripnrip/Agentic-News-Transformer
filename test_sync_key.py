#!/usr/bin/env python3
"""
Test script to verify the new Sync.so API key is being loaded correctly.
"""
import os
from dotenv import load_dotenv
from avatar_generator import AvatarGenerationAgent

def test_sync_key():
    print("🔧 Testing Sync.so API Key...")
    
    # Load environment variables
    load_dotenv()
    
    # Check if key is loaded from environment
    sync_key = os.getenv('SYNC_SO_API_KEY')
    if sync_key:
        print(f"✅ API Key loaded from environment: {sync_key[:10]}...{sync_key[-10:]}")
        print(f"📏 Key length: {len(sync_key)}")
    else:
        print("❌ No API Key found in environment")
        return False
    
    # Test avatar agent initialization
    try:
        print("\n🤖 Initializing AvatarGenerationAgent...")
        avatar_agent = AvatarGenerationAgent()
        print("✅ AvatarGenerationAgent initialized successfully")
        
        # Check if the agent has the correct API key
        if hasattr(avatar_agent, 'sync_api_key'):
            print(f"✅ Agent has API key: {avatar_agent.sync_api_key[:10]}...{avatar_agent.sync_api_key[-10:]}")
            
            # Compare keys
            if avatar_agent.sync_api_key == sync_key:
                print("✅ API Key matches between environment and agent")
                return True
            else:
                print("❌ API Key mismatch between environment and agent")
                return False
        else:
            print("❌ Agent doesn't have sync_api_key attribute")
            return False
            
    except Exception as e:
        print(f"❌ Error initializing AvatarGenerationAgent: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_sync_key()
    if success:
        print("\n🎉 API Key test passed! Ready to use the new key.")
    else:
        print("\n❌ API Key test failed. Please check the configuration.")