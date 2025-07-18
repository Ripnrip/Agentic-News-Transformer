#!/usr/bin/env python3
"""
Batch pipeline that processes 10 articles:
1. Fetches 10 news articles using NewsDataHub
2. Generates scripts from each article
3. Creates audio using OpenAI TTS
4. Produces lip-synced videos with Sync.so
5. Uploads all assets to S3
"""
import os
import json
import time
from agents import NewsSearchAgent, NewsAPIClient, NewsDataHubClient
from content_generator import ContentGenerationAgent, ArticleRequest
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent
from database_agent import DatabaseAgent

def process_single_article(article, index, content_agent, audio_agent, avatar_agent):
    """Process a single article through the complete pipeline."""
    print(f"\n{'='*50}")
    print(f"📰 Processing Article {index + 1}/10: {article.title[:50]}...")
    print(f"{'='*50}")
    
    try:
        # Step 1: Generate script from article
        print(f"📝 Step 1: Generating script...")
        article_text = article.title
        if hasattr(article, 'content') and article.content:
            content_text = str(article.content)
            if hasattr(article.content, 'text'):
                content_text = article.content.text
            article_text += ". " + content_text[:500]  # Limit content length
        
        script_result = content_agent.generate_article_content(ArticleRequest(topic=article_text))
        
        if not script_result:
            print("❌ Failed to generate script. Skipping article.")
            return None
        
        script = script_result.content
        print(f"✅ Generated script: {script_result.title}")
        print(f"📄 Script length: {len(script)} characters")
        
        # Step 2: Generate audio from script
        print(f"🔊 Step 2: Generating audio...")
        safe_title = "".join(c for c in article.title if c.isalnum() or c in (' ', '-', '_'))[:30]
        audio_request = AudioRequest(
            text=script,
            title=f"News_{index+1}_{safe_title}",
            upload_to_s3=True,
            voice="nova"  # OpenAI voice
        )
        audio_result = audio_agent.generate_audio_content(audio_request)
        
        if not audio_result or not audio_result.audio_file:
            print("❌ Failed to generate audio. Skipping article.")
            return None
        
        print(f"✅ Generated audio: {audio_result.audio_file}")
        if audio_result.s3_url:
            print(f"🔗 Audio S3 URL: {audio_result.s3_url}")
        
        # Step 3: Generate video from audio
        print(f"🎬 Step 3: Generating lip-synced video...")
        video_result = avatar_agent.generate_video(
            audio_file=audio_result.audio_file,
            audio_url=audio_result.s3_url if audio_result.s3_url else None,
            avatar_name="Professional News Anchor",
            poll_for_completion=True,
            indefinite_polling=False,  # Don't wait indefinitely for batch processing
            max_poll_time=300  # 5 minutes max per video
        )
        
        if not video_result:
            print("❌ Failed to generate video. Skipping.")
            return None
        
        print(f"✅ Generated video successfully")
        if hasattr(video_result, 's3_video_url'):
            print(f"🔗 Video S3 URL: {video_result.s3_video_url}")
        
        # Return summary
        return {
            "index": index + 1,
            "article_title": article.title,
            "script_title": script_result.title,
            "audio_file": audio_result.audio_file,
            "audio_s3_url": audio_result.s3_url,
            "video_result": video_result,
            "video_s3_url": getattr(video_result, 's3_video_url', None),
            "success": True
        }
        
    except Exception as e:
        print(f"❌ Error processing article {index + 1}: {str(e)}")
        return {
            "index": index + 1,
            "article_title": article.title,
            "error": str(e),
            "success": False
        }

def main():
    print("🚀 Starting Batch Agentic Content Transformer Pipeline...")
    print("📊 Target: Process 10 articles into videos")
    
    # Initialize agents
    print("\n🔧 Initializing agents...")
    try:
        content_agent = ContentGenerationAgent(DatabaseAgent())
        audio_agent = AudioGenerationAgent()
        avatar_agent = AvatarGenerationAgent()
        print("✅ All agents initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize agents: {str(e)}")
        return
    
    # Step 1: Fetch news articles
    print("\n📰 Step 1: Fetching 10 news articles...")
    news_agent = NewsSearchAgent(article_limit=10)
    
    # Try multiple sources for better coverage
    articles = []
    
    # Try NewsDataHub first
    try:
        newsdata_hub_client = NewsDataHubClient()
        articles.extend(newsdata_hub_client.fetch_ai_news(days_back=7, limit=10))
        print(f"📰 NewsDataHub: Found {len(articles)} articles")
    except Exception as e:
        print(f"⚠️ NewsDataHub error: {str(e)}")
    
    # Try NewsAPI if we need more articles
    if len(articles) < 10:
        try:
            newsapi_client = NewsAPIClient()
            newsapi_articles = newsapi_client.fetch_ai_news(days_back=7, limit=10 - len(articles))
            articles.extend(newsapi_articles)
            print(f"📰 NewsAPI: Total articles now {len(articles)}")
        except Exception as e:
            print(f"⚠️ NewsAPI error: {str(e)}")
    
    # Try NewsSearchAgent method if still need more
    if len(articles) < 10:
        try:
            agent_articles = news_agent.fetch_ai_news_from_newsapi()
            articles.extend(agent_articles)
            print(f"📰 NewsSearchAgent: Total articles now {len(articles)}")
        except Exception as e:
            print(f"⚠️ NewsSearchAgent error: {str(e)}")
    
    if not articles:
        print("❌ No articles found. Exiting.")
        return
    
    # Limit to 10 articles
    articles = articles[:10]
    print(f"✅ Found {len(articles)} articles to process.")
    
    # Step 2: Process each article
    print(f"\n🔄 Step 2: Processing {len(articles)} articles...")
    
    results = []
    successful_videos = []
    failed_articles = []
    
    for i, article in enumerate(articles):
        result = process_single_article(article, i, content_agent, audio_agent, avatar_agent)
        results.append(result)
        
        if result and result.get('success'):
            successful_videos.append(result)
        else:
            failed_articles.append(result)
        
        # Small delay between articles to avoid rate limiting
        if i < len(articles) - 1:
            print(f"⏳ Waiting 10 seconds before next article...")
            time.sleep(10)
    
    # Step 3: Final report
    print("\n🏁 Batch Processing Complete!")
    print(f"📊 Summary:")
    print(f"   • Total articles processed: {len(articles)}")
    print(f"   • Successful videos: {len(successful_videos)}")
    print(f"   • Failed articles: {len(failed_articles)}")
    
    if successful_videos:
        print(f"\n✅ Successfully created {len(successful_videos)} videos:")
        for result in successful_videos:
            print(f"   {result['index']}. {result['article_title'][:50]}...")
            if result.get('video_s3_url'):
                print(f"      🔗 Video: {result['video_s3_url']}")
            if result.get('audio_s3_url'):
                print(f"      🔗 Audio: {result['audio_s3_url']}")
    
    if failed_articles:
        print(f"\n❌ Failed to process {len(failed_articles)} articles:")
        for result in failed_articles:
            if result:
                print(f"   {result['index']}. {result['article_title'][:50]}...")
                if result.get('error'):
                    print(f"      Error: {result['error']}")
    
    # Save results to file
    output_file = f"batch_results_{time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Results saved to: {output_file}")
    
    return {
        "total_articles": len(articles),
        "successful_videos": len(successful_videos),
        "failed_articles": len(failed_articles),
        "results": results,
        "output_file": output_file
    }

if __name__ == "__main__":
    main()