#!/usr/bin/env python3
"""
Complete pipeline that:
1. Fetches news articles using NewsDataHub
2. Generates a script from the first article
3. Creates audio using ElevenLabs
4. Produces a lip-synced video with Sync.so
5. Uploads all assets to S3
"""
import os
import json
import time
from agents import NewsSearchAgent, NewsAPIClient, NewsDataHubClient
from content_generator import ContentGenerationAgent, ArticleRequest
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent

def main():
    print("🚀 Starting Agentic Content Transformer pipeline...")
    
    # Step 1: Fetch news articles
    print("\n📰 Step 1: Fetching news articles...")
    agent = NewsSearchAgent(article_limit=5)
    newsdata_hub_client = NewsDataHubClient()
    articles = newsdata_hub_client.fetch_ai_news(days_back=7, limit=5)
    
    if not articles:
        print("❌ No articles found. Exiting.")
        return
    
    print(f"✅ Found {len(articles)} articles.")
    
    # Step 2: Generate script from the first article
    print("\n📝 Step 2: Generating script from first article...")
    first_article = articles[0]
    print(f"🔍 Using article: {first_article.title}")
    
    # Extract article content as a string
    print("📄 Extracting article content...")
    article_text = first_article.title + ". " + first_article.description if hasattr(first_article, 'description') else first_article.title
    print(f"📄 Article text: {article_text[:150]}...")
    
    # Get article content
    content_agent = ContentGenerationAgent()
    script_result = content_agent.generate_article_content(ArticleRequest(topic=article_text))
    
    if not script_result:
        print("❌ Failed to generate script. Exiting.")
        return
    
    script = script_result.content
    print(f"✅ Generated script: {script_result.title}")
    print(f"📄 Script length: {len(script)} characters")
    
    # Step 3: Generate audio from script
    print("\n🔊 Step 3: Generating audio from script...")
    audio_agent = AudioGenerationAgent()
    audio_request = AudioRequest(
        text=script,
        title=f"News_Script_{first_article.title[:20]}",
        upload_to_s3=True
    )
    audio_result = audio_agent.generate_audio_content(audio_request)
    
    if not audio_result or not audio_result.audio_url:
        print("❌ Failed to generate audio. Exiting.")
        return
    
    print(f"✅ Generated audio: {audio_result.audio_url}")
    
    # Step 4: Generate video from audio
    print("\n🎬 Step 4: Generating lip-synced video...")
    avatar_agent = AvatarGenerationAgent()
    video_result = avatar_agent.generate_video(
        audio_file=audio_result.audio_file,
        audio_url=audio_result.audio_url,
        avatar_name="Sexy News Anchor",
        poll_for_completion=True,
        indefinite_polling=True
    )
    
    if not video_result or not hasattr(video_result, 's3_video_url'):
        print("❌ Failed to generate video.")
        return
    
    print(f"✅ Generated video: {video_result.s3_video_url}")
    
    # Final report
    print("\n🏁 Pipeline Completed Successfully!")
    print("📰 Article: " + first_article.title)
    print("🎵 Audio: " + audio_result.audio_url)
    print("🎬 Video: " + video_result.s3_video_url)
    
    return {
        "article": first_article.title,
        "audio": audio_result.audio_url,
        "video": video_result.s3_video_url
    }

if __name__ == "__main__":
    main() 