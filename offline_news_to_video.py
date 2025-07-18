#!/usr/bin/env python3
"""Offline pipeline to fetch AI-related news and create short avatar videos.

This script fetches articles from Google News RSS, generates audio with OpenAI
TTS and then uses Sync.so to produce lip-synced videos. Videos are saved to a
dated folder and uploaded to S3 if credentials are available."""
import os
from datetime import datetime
import feedparser
from dotenv import load_dotenv
from audio_generator import AudioGenerationAgent, AudioRequest
from avatar_generator import AvatarGenerationAgent

load_dotenv()



def sanitize_filename(name: str) -> str:
    return ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in name)[:50]


def fetch_articles(limit: int = 5):
    rss_url = "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)
    return feed.entries[:limit]


def generate_video(article, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    title = article.get("title", "No Title")
    summary = article.get("summary", "")
    text = f"{title}. {summary}"
    base = sanitize_filename(title)

    # Initialize agents after setting OUTPUT_DIR so avatar videos are saved to the
    # correct folder
    os.environ["OUTPUT_DIR"] = out_dir
    audio_agent = AudioGenerationAgent()
    avatar_agent = AvatarGenerationAgent()

    # Generate audio using OpenAI TTS
    audio_request = AudioRequest(text=text, title=base, output_dir=out_dir, upload_to_s3=True)
    audio_result = audio_agent.generate_audio_content(audio_request)
    if not audio_result or not audio_result.audio_file:
        print("Failed to generate audio")
        return None

    # Generate video with Sync.so
    video_result = avatar_agent.generate_video(
        audio_file=audio_result.audio_file,
        audio_url=audio_result.audio_url,
        avatar_name="Sexy News Anchor",
        poll_for_completion=True,
    )

    if not video_result or video_result.status != "COMPLETED":
        print("Video generation failed")
        return None

    # Move downloaded video to output directory if necessary
    local_files = [f for f in os.listdir(out_dir) if f.endswith(".mp4")]
    if local_files:
        return os.path.join(out_dir, local_files[-1])

    return None



def main():
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join("output", today)
    articles = fetch_articles(limit=5)
    if not articles:
        print("No articles found")
        return
    for i, article in enumerate(articles, 1):
        print(f"Creating video {i}/{len(articles)}: {article.get('title')}")
        video_path = generate_video(article, out_dir)
        print(f"Saved: {video_path}")
    print(f"Videos saved to {out_dir}")


if __name__ == "__main__":
    main()
