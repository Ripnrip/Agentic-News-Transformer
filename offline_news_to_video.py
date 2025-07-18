#!/usr/bin/env python3
"""Simple pipeline to fetch AI-related news from Google News RSS and turn them into short videos using gTTS and moviepy."""
import os
from datetime import datetime
import feedparser
from gtts import gTTS
from moviepy import TextClip, AudioFileClip
from audio_generator import upload_file_to_s3


def sanitize_filename(name: str) -> str:
    return ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in name)[:50]


def fetch_articles(limit: int = 10):
    rss_url = "https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)
    return feed.entries[:limit]


def generate_video(article, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    title = article.get('title', 'No Title')
    summary = article.get('summary', '')
    text = f"{title}. {summary}"
    base = sanitize_filename(title)
    audio_path = os.path.join(out_dir, f"{base}.mp3")
    video_path = os.path.join(out_dir, f"{base}.mp4")

    # Generate TTS audio
    tts = gTTS(text=text, lang='en')
    tts.save(audio_path)

    # Create simple video with title text
    audio = AudioFileClip(audio_path)
    clip = TextClip(text=title, font_size=50, color='white', bg_color='black', size=(640, 480))
    video = clip.with_audio(audio).with_duration(audio.duration)
    video.write_videofile(video_path, fps=24, logger=None)

    # Upload to S3 if credentials are provided
    s3_url = None
    if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
        s3_url = upload_file_to_s3(video_path)
        if s3_url:
            print(f"Uploaded to S3: {s3_url}")

    return video_path


def main():
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = os.path.join("output", today)
    articles = fetch_articles(limit=10)
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
