#!/usr/bin/env python3
"""
Batch processor for 10 articles using RSS and Playwright scraping.
No NewsDataHub - uses RSS feeds and Playwright for scraping.
"""
import os
import json
import time
from datetime import datetime
from dotenv import load_dotenv
from agents import NewsSearchAgent, NewsAPIClient
from content_generator import ContentGenerationAgent, ArticleRequest
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent
from database_agent import DatabaseAgent

# Load environment variables
load_dotenv()

def process_article(article, index, content_agent, audio_agent, avatar_agent):
    """Process a single article through the pipeline."""
    print(f"\n{'='*60}")
    print(f"🔄 Processing Article {index + 1}/10")
    print(f"📰 Title: {article.title[:70]}...")
    print(f"🔗 Source: {article.source}")
    print(f"{'='*60}")
    
    try:
        # Step 1: Generate script
        print("📝 Step 1: Generating script...")
        
        # Use article title and content for script generation
        topic_text = article.title
        if hasattr(article, 'content') and article.content:
            content_text = str(article.content)
            if len(content_text) > 200:
                topic_text += f". {content_text[:300]}..."
        
        script_request = ArticleRequest(
            topic=topic_text,
            tone="professional",
            length="short"  # For 30-second videos
        )
        
        script_result = content_agent.generate_article_content(script_request)
        
        if not script_result or not script_result.content:
            print("❌ Failed to generate script")
            return {"success": False, "error": "Script generation failed"}
        
        print(f"✅ Script generated: {len(script_result.content)} characters")
        
        # Step 2: Generate audio
        print("🔊 Step 2: Generating audio with OpenAI TTS...")
        
        # Clean title for filename
        safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_'))[:30]
        safe_title = safe_title.replace(' ', '_')
        
        audio_request = AudioRequest(
            text=script_result.content,
            title=f"Article_{index+1:02d}_{safe_title}",
            voice="nova",  # OpenAI voice
            upload_to_s3=True,
            output_dir="generated_audio"
        )
        
        audio_result = audio_agent.generate_audio_content(audio_request)
        
        if not audio_result or not audio_result.audio_file:
            print("❌ Failed to generate audio")
            return {"success": False, "error": "Audio generation failed"}
        
        print(f"✅ Audio generated: {audio_result.audio_file}")
        if audio_result.s3_url:
            print(f"🔗 Audio S3 URL: {audio_result.s3_url}")
        
        # Step 3: Generate video
        print("🎬 Step 3: Generating lip-sync video with Sync.so...")
        
        video_result = avatar_agent.generate_video(
            audio_file=audio_result.audio_file,
            audio_url=audio_result.s3_url,
            avatar_name="Sexy News Anchor",  # This is the only available avatar
            poll_for_completion=True,
            indefinite_polling=False,
            max_attempts=30  # Maximum polling attempts
        )
        
        if not video_result:
            print("❌ Failed to generate video")
            return {
                "success": False, 
                "error": "Video generation failed",
                "audio_file": audio_result.audio_file,
                "audio_s3_url": audio_result.s3_url
            }
        
        print("✅ Video generated successfully!")
        
        # Extract video URL
        video_url = None
        if hasattr(video_result, 's3_video_url'):
            video_url = video_result.s3_video_url
        elif hasattr(video_result, 'video_url'):
            video_url = video_result.video_url
        
        if video_url:
            print(f"🔗 Video URL: {video_url}")
        
        return {
            "success": True,
            "index": index + 1,
            "article_title": article.title,
            "article_source": article.source,
            "article_link": article.link,
            "script_title": script_result.title,
            "script_content": script_result.content,
            "audio_file": audio_result.audio_file,
            "audio_s3_url": audio_result.s3_url,
            "video_url": video_url,
            "video_result": str(video_result)
        }
        
    except Exception as e:
        print(f"❌ Error processing article {index + 1}: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "index": index + 1,
            "article_title": article.title
        }

def main():
    print("🚀 Batch Article to Video Pipeline")
    print("📊 Target: 3 articles using RSS/Playwright scraping")
    print("🚫 No NewsDataHub - using Google RSS and Playwright")
    
    # Initialize agents
    print("\n🔧 Initializing agents...")
    try:
        db_agent = DatabaseAgent()
        content_agent = ContentGenerationAgent(db_agent)
        audio_agent = AudioGenerationAgent()
        avatar_agent = AvatarGenerationAgent()
        news_agent = NewsSearchAgent(article_limit=3)
        print("✅ All agents initialized")
    except Exception as e:
        print(f"❌ Agent initialization failed: {str(e)}")
        return
    
    # Fetch articles using multiple methods
    print("\n📰 Fetching articles using RSS and Playwright...")
    articles = []
    
    # Method 1: Try NewsAPI first (if available)
    try:
        newsapi_client = NewsAPIClient()
        if newsapi_client.api_key:
            print("🔍 Trying NewsAPI...")
            newsapi_articles = newsapi_client.fetch_ai_news(days_back=7, limit=3)
            articles.extend(newsapi_articles)
            print(f"✅ NewsAPI: Found {len(newsapi_articles)} articles")
        else:
            print("⚠️ NewsAPI key not available")
    except Exception as e:
        print(f"⚠️ NewsAPI error: {str(e)}")
    
    # Method 2: RSS Feed fallback
    if len(articles) < 3:
        try:
            print("🔍 Trying Google RSS feed...")
            rss_articles = news_agent.fetch_ai_news_from_rss(limit=3 - len(articles))
            articles.extend(rss_articles)
            print(f"✅ RSS: Found {len(rss_articles)} articles (total: {len(articles)})")
        except Exception as e:
            print(f"⚠️ RSS error: {str(e)}")
    
    # Method 3: Playwright scraping fallback
    if len(articles) < 3:
        try:
            print("🔍 Trying Playwright scraping...")
            playwright_articles = news_agent.fetch_ai_news_with_playwright(limit=3 - len(articles))
            articles.extend(playwright_articles)
            print(f"✅ Playwright: Found {len(playwright_articles)} articles (total: {len(articles)})")
        except Exception as e:
            print(f"⚠️ Playwright error: {str(e)}")
    
    if not articles:
        print("❌ No articles found with any method. Exiting.")
        return
    
    # Limit to 3 articles
    articles = articles[:3]
    print(f"\n🎯 Processing {len(articles)} articles")
    
    # Process each article
    results = []
    successful_videos = []
    
    for i, article in enumerate(articles):
        result = process_article(article, i, content_agent, audio_agent, avatar_agent)
        results.append(result)
        
        if result.get("success"):
            successful_videos.append(result)
            print(f"✅ Article {i+1} completed successfully")
        else:
            print(f"❌ Article {i+1} failed: {result.get('error', 'Unknown error')}")
        
        # Delay between articles to avoid rate limiting
        if i < len(articles) - 1:
            print("⏳ Waiting 15 seconds before next article...")
            time.sleep(15)
    
    # Final summary
    print(f"\n🏁 Batch Processing Complete!")
    print(f"📊 Results Summary:")
    print(f"   • Total articles: {len(articles)}")
    print(f"   • Successful videos: {len(successful_videos)}")
    print(f"   • Failed attempts: {len(articles) - len(successful_videos)}")
    
    # Show successful videos
    if successful_videos:
        print(f"\n✅ Successfully created {len(successful_videos)} videos:")
        for result in successful_videos:
            print(f"   {result['index']}. {result['article_title'][:50]}...")
            if result.get('video_url'):
                print(f"      🎬 Video: {result['video_url']}")
            if result.get('audio_s3_url'):
                print(f"      🔊 Audio: {result['audio_s3_url']}")
    
    # Show failed articles
    failed_results = [r for r in results if not r.get("success")]
    if failed_results:
        print(f"\n❌ Failed to process {len(failed_results)} articles:")
        for result in failed_results:
            print(f"   {result.get('index', '?')}. {result.get('article_title', 'Unknown')[:50]}...")
            if result.get('error'):
                print(f"      Error: {result['error']}")
    
    # Save results to JSON
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"batch_results_{timestamp}.json"
    
    try:
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n💾 Results saved to: {output_file}")
    except Exception as e:
        print(f"⚠️ Failed to save results: {str(e)}")
    
    # Print AWS S3 links summary
    if successful_videos:
        print(f"\n🔗 AWS S3 Links Summary:")
        print("="*80)
        for result in successful_videos:
            print(f"Article {result['index']}: {result['article_title'][:40]}...")
            if result.get('audio_s3_url'):
                print(f"  Audio:  {result['audio_s3_url']}")
            if result.get('video_url'):
                print(f"  Video:  {result['video_url']}")
            print("-" * 80)
    
    return {
        "total_articles": len(articles),
        "successful_videos": len(successful_videos),
        "failed_articles": len(failed_results),
        "results": results
    }

if __name__ == "__main__":
    main()