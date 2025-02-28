"""Agent for distributing content across social media platforms using Pydantic models."""
import os
import json
import time
from typing import Dict, List, Optional, Union, Any
from datetime import datetime, timedelta
import requests
from dotenv import load_dotenv
from pydantic import BaseModel, Field, validator

# Platform-specific libraries
import tweepy  # For X (formerly Twitter)
import facebook  # For Facebook
from linkedin_api import Linkedin  # For LinkedIn

# Load environment variables
load_dotenv()

# -------------- Pydantic Models --------------

class MediaFile(BaseModel):
    """Model for media file data."""
    path: str
    type: str = "image"  # image, video, audio
    
    @validator('type')
    def validate_media_type(cls, v):
        if v not in ["image", "video", "audio"]:
            raise ValueError(f"Media type must be one of: image, video, audio")
        return v

class Credentials(BaseModel):
    """Base model for platform credentials."""
    platform: str

class XCredentials(Credentials):
    """Credentials for X (Twitter) API."""
    platform: str = "x"
    api_key: str
    api_secret: str
    bearer_token: str
    access_token: str
    access_token_secret: str

class FacebookCredentials(Credentials):
    """Credentials for Facebook API."""
    platform: str = "facebook"
    access_token: str
    page_id: str

class LinkedInCredentials(Credentials):
    """Credentials for LinkedIn API."""
    platform: str = "linkedin"
    email: str
    password: str

class PostContent(BaseModel):
    """Model for content to be posted."""
    headline: str
    intro: Optional[str] = ""
    body: Optional[str] = ""
    conclusion: Optional[str] = ""
    hashtags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class PostResult(BaseModel):
    """Model for post result."""
    success: bool
    platform: str
    post_id: Optional[str] = None
    error: Optional[str] = None
    url: Optional[str] = None

class ScheduleOptions(BaseModel):
    """Model for scheduling options."""
    post_time: datetime
    platforms: List[str]
    content: PostContent
    media_files: Optional[Dict[str, List[str]]] = None
    personalities: Optional[Dict[str, str]] = None

# -------------- Platform Classes --------------

class SocialMediaPlatform:
    """Base class for social media platform adapters."""
    
    def __init__(self, credentials: Credentials):
        """Initialize platform with API credentials."""
        self.credentials = credentials
        self.client = None
        self.platform_name = credentials.platform
        self.character_limit = 5000  # Default
        self.connect()
    
    def connect(self):
        """Connect to platform API."""
        raise NotImplementedError("Subclasses must implement connect()")
    
    def post_content(self, text: str, media: Optional[List[str]] = None) -> PostResult:
        """Post content to platform."""
        raise NotImplementedError("Subclasses must implement post_content()")
    
    def format_content(self, content: PostContent, personality: str) -> str:
        """Format content for platform based on personality."""
        raise NotImplementedError("Subclasses must implement format_content()")


class XPlatform(SocialMediaPlatform):
    """X (formerly Twitter) platform adapter."""
    
    def __init__(self, credentials: XCredentials):
        self.character_limit = 280
        super().__init__(credentials)
    
    def connect(self):
        """Connect to X API using v2 endpoint."""
        self.client = tweepy.Client(
            bearer_token=self.credentials.bearer_token,
            consumer_key=self.credentials.api_key, 
            consumer_secret=self.credentials.api_secret,
            access_token=self.credentials.access_token, 
            access_token_secret=self.credentials.access_token_secret
        )
        # For media uploads
        self.auth = tweepy.OAuth1UserHandler(
            self.credentials.api_key,
            self.credentials.api_secret,
            self.credentials.access_token,
            self.credentials.access_token_secret
        )
        self.api = tweepy.API(self.auth)
    
    def post_content(self, text: str, media: Optional[List[str]] = None) -> PostResult:
        """Post content to X."""
        try:
            media_ids = []
            if media:
                for media_file in media:
                    if media_file.endswith(('.mp4', '.mov')):
                        # Handle video upload
                        media_id = self.api.media_upload(
                            filename=media_file,
                            media_category='tweet_video'
                        ).media_id
                    elif media_file.endswith(('.mp3', '.wav')):
                        # Handle audio upload (treated as video in X API)
                        media_id = self.api.media_upload(
                            filename=media_file,
                            media_category='tweet_video'
                        ).media_id
                    else:
                        # Handle image upload
                        media_id = self.api.media_upload(filename=media_file).media_id
                    media_ids.append(media_id)
            
            # Post tweet with media using v2 API
            if media_ids:
                response = self.client.create_tweet(
                    text=text,
                    media_ids=media_ids
                )
            else:
                response = self.client.create_tweet(text=text)
                
            tweet_id = response.data['id']
            
            return PostResult(
                success=True,
                post_id=tweet_id,
                platform=self.platform_name,
                url=f"https://x.com/i/web/status/{tweet_id}"
            )
            
        except Exception as e:
            return PostResult(
                success=False,
                error=str(e),
                platform=self.platform_name
            )
    
    def format_content(self, content: PostContent, personality: str) -> str:
        """Format content for X with character limits."""
        headline = content.headline
        hashtags = ' '.join([h if h.startswith('#') else f'#{h}' for h in content.hashtags])
        
        # Different personality formats
        if personality == "professional":
            text = f"{headline}\n\n{hashtags}"
        elif personality == "casual":
            text = f"Check this out! {headline} {hashtags}"
        elif personality == "enthusiastic":
            text = f"OMG! 🔥 {headline} {hashtags}"
        else:
            text = f"{headline} {hashtags}"
            
        # Ensure we don't exceed character limit
        if len(text) > self.character_limit:
            # Truncate and add ellipsis
            text = text[:self.character_limit - 3] + "..."
            
        return text


class FacebookPlatform(SocialMediaPlatform):
    """Facebook platform adapter."""
    
    def __init__(self, credentials: FacebookCredentials):
        self.character_limit = 63206  # Facebook's limit
        super().__init__(credentials)
    
    def connect(self):
        """Connect to Facebook Graph API."""
        self.client = facebook.GraphAPI(
            access_token=self.credentials.access_token,
            version="v17.0"
        )
    
    def post_content(self, text: str, media: Optional[List[str]] = None) -> PostResult:
        """Post content to Facebook page."""
        try:
            page_id = self.credentials.page_id
            
            # Handle different media types
            if media and media[0].endswith(('.mp4', '.mov')):
                # Video upload
                response = self.client.put_video(
                    title=text[:100],  # Use first 100 chars as title
                    description=text,
                    video_path=media[0],
                    target_id=page_id
                )
            elif media and media[0].endswith(('.mp3', '.wav')):
                # Audio upload - Facebook treats this as a video
                response = self.client.put_video(
                    title=text[:100],
                    description=text,
                    video_path=media[0],
                    target_id=page_id
                )
            elif media:
                # Photo upload
                response = self.client.put_photo(
                    image=open(media[0], 'rb'),
                    message=text
                )
            else:
                # Text-only post
                response = self.client.put_object(
                    parent_object=page_id,
                    connection_name="feed",
                    message=text
                )
            
            post_id = response.get('id', '')
            
            return PostResult(
                success=True,
                post_id=post_id,
                platform=self.platform_name,
                url=f"https://facebook.com/{post_id}"
            )
            
        except Exception as e:
            return PostResult(
                success=False,
                error=str(e),
                platform=self.platform_name
            )
    
    def format_content(self, content: PostContent, personality: str) -> str:
        """Format content for Facebook."""
        headline = content.headline
        intro = content.intro
        hashtags = ' '.join([h if h.startswith('#') else f'#{h}' for h in content.hashtags])
        
        # Different personality formats
        if personality == "professional":
            text = f"{headline}\n\n{intro}\n\n{hashtags}"
        elif personality == "casual":
            text = f"Hey everyone! Check this out:\n\n{headline}\n\n{intro}\n\n{hashtags}"
        elif personality == "storyteller":
            text = f"I wanted to share something interesting with you today...\n\n{headline}\n\n{intro}\n\n{hashtags}"
        else:
            text = f"{headline}\n\n{intro}\n\n{hashtags}"
            
        return text


class LinkedInPlatform(SocialMediaPlatform):
    """LinkedIn platform adapter."""
    
    def __init__(self, credentials: LinkedInCredentials):
        self.character_limit = 3000
        super().__init__(credentials)
    
    def connect(self):
        """Connect to LinkedIn API."""
        self.client = Linkedin(
            self.credentials.email,
            self.credentials.password
        )
    
    def post_content(self, text: str, media: Optional[List[str]] = None) -> PostResult:
        """Post content to LinkedIn."""
        try:
            # Submit share on LinkedIn
            if media and any(media_file.endswith(('.mp4', '.mov')) for media_file in media):
                # Video upload - use first video found
                video_path = next(m for m in media if m.endswith(('.mp4', '.mov')))
                urn = self.client.post_video(
                    text=text,
                    video_path=video_path
                )
            elif media:
                # Image upload - use first image found
                image_path = media[0]
                urn = self.client.post_image(
                    text=text,
                    image_path=image_path
                )
            else:
                # Text-only post
                urn = self.client.post(text=text)
            
            # The URN is the LinkedIn identifier for the post
            if urn:
                post_id = urn.split(":")[-1]
                return PostResult(
                    success=True,
                    post_id=post_id,
                    platform=self.platform_name,
                    url=f"https://www.linkedin.com/feed/update/{urn}"
                )
            else:
                return PostResult(
                    success=False,
                    error="No post URN returned",
                    platform=self.platform_name
                )
                
        except Exception as e:
            return PostResult(
                success=False,
                error=str(e),
                platform=self.platform_name
            )
    
    def format_content(self, content: PostContent, personality: str) -> str:
        """Format content for LinkedIn."""
        headline = content.headline
        intro = content.intro
        conclusion = content.conclusion
        hashtags = ' '.join([h if h.startswith('#') else f'#{h}' for h in content.hashtags])
        
        # Different personality formats for professional platform
        if personality == "thought_leader":
            text = f"# {headline}\n\n{intro}\n\n{conclusion}\n\n{hashtags}"
        elif personality == "industry_expert":
            text = f"I'm excited to share my thoughts on {headline}\n\n{intro}\n\n{conclusion}\n\n{hashtags}"
        elif personality == "educator":
            text = f"Today I want to teach you about: {headline}\n\n{intro}\n\n{conclusion}\n\nWhat do you think? Let's discuss in the comments.\n\n{hashtags}"
        else:
            text = f"{headline}\n\n{intro}\n\n{conclusion}\n\n{hashtags}"
            
        # Ensure we don't exceed character limit
        if len(text) > self.character_limit:
            # Truncate and add ellipsis
            text = text[:self.character_limit - 3] + "..."
            
        return text


class SocialMediaAgent:
    """Agent for distributing content across social media platforms."""
    
    def __init__(self):
        """Initialize social media agent with platform adapters."""
        # Platform personality mappings
        self.platform_personalities = {
            "x": "casual",
            "facebook": "storyteller",
            "linkedin": "thought_leader",
            "instagram": "visual",
        }
        
        # Initialize platform connections
        self.platforms = {}
        self._initialize_platforms()
        
    def _initialize_platforms(self):
        """Initialize connections to all configured platforms."""
        # X (formerly Twitter)
        if os.getenv("X_API_KEY"):
            try:
                x_creds = XCredentials(
                    api_key=os.getenv("X_API_KEY"),
                    api_secret=os.getenv("X_API_SECRET"),
                    bearer_token=os.getenv("X_BEARER_TOKEN"),
                    access_token=os.getenv("X_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("X_ACCESS_SECRET")
                )
                self.platforms["x"] = XPlatform(x_creds)
                print("X (Twitter) connection initialized")
            except Exception as e:
                print(f"Failed to initialize X platform: {e}")
            
        # For backward compatibility - check Twitter env vars if X not found
        elif os.getenv("TWITTER_API_KEY"):
            try:
                x_creds = XCredentials(
                    api_key=os.getenv("TWITTER_API_KEY"),
                    api_secret=os.getenv("TWITTER_API_SECRET"),
                    bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
                    access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
                    access_token_secret=os.getenv("TWITTER_ACCESS_SECRET")
                )
                self.platforms["x"] = XPlatform(x_creds)
                print("X (Twitter) connection initialized using legacy Twitter credentials")
            except Exception as e:
                print(f"Failed to initialize X platform with Twitter credentials: {e}")
            
        # Facebook
        if os.getenv("FACEBOOK_ACCESS_TOKEN"):
            try:
                fb_creds = FacebookCredentials(
                    access_token=os.getenv("FACEBOOK_ACCESS_TOKEN"),
                    page_id=os.getenv("FACEBOOK_PAGE_ID")
                )
                self.platforms["facebook"] = FacebookPlatform(fb_creds)
                print("Facebook connection initialized")
            except Exception as e:
                print(f"Failed to initialize Facebook platform: {e}")
            
        # LinkedIn
        if os.getenv("LINKEDIN_EMAIL"):
            try:
                linkedin_creds = LinkedInCredentials(
                    email=os.getenv("LINKEDIN_EMAIL"),
                    password=os.getenv("LINKEDIN_PASSWORD")
                )
                self.platforms["linkedin"] = LinkedInPlatform(linkedin_creds)
                print("LinkedIn connection initialized")
            except Exception as e:
                print(f"Failed to initialize LinkedIn platform: {e}")
    
    def _convert_to_post_content(self, content_dict: Dict) -> PostContent:
        """Convert a dictionary to a PostContent object."""
        hashtags = content_dict.get('metadata', {}).get('hashtags', [])
        return PostContent(
            headline=content_dict.get('headline', ''),
            intro=content_dict.get('intro', ''),
            body=content_dict.get('body', ''),
            conclusion=content_dict.get('conclusion', ''),
            hashtags=hashtags,
            metadata=content_dict.get('metadata', {})
        )
    
    def post_to_platforms(self, 
                         content: Dict, 
                         media_files: Optional[Dict[str, List[str]]] = None, 
                         platforms: Optional[List[str]] = None,
                         custom_personalities: Optional[Dict[str, str]] = None) -> Dict[str, PostResult]:
        """
        Post content to specified social media platforms.
        
        Args:
            content: Content dict with headline, intro, body, conclusion
            media_files: Dict mapping platform to media file paths
            platforms: List of platforms to post to (uses all available if None)
            custom_personalities: Override default personalities by platform
            
        Returns:
            Dict with results for each platform
        """
        results = {}
        
        # Convert content dict to PostContent model
        post_content = self._convert_to_post_content(content)
        
        # Use specified platforms or all available
        target_platforms = platforms or list(self.platforms.keys())
        
        # Combine default and custom personalities
        personalities = self.platform_personalities.copy()
        if custom_personalities:
            personalities.update(custom_personalities)
        
        # Post to each platform
        for platform_name in target_platforms:
            platform = self.platforms.get(platform_name)
            
            if not platform:
                results[platform_name] = PostResult(
                    success=False,
                    error="Platform not configured",
                    platform=platform_name
                )
                continue
            
            # Get personality for this platform
            personality = personalities.get(platform_name, "default")
            
            # Format content for platform
            formatted_text = platform.format_content(post_content, personality)
            
            # Get media for this platform
            media = media_files.get(platform_name, []) if media_files else None
            
            # Post to platform and store result
            result = platform.post_content(formatted_text, media)
            results[platform_name] = result
            
            # Delay between posts to avoid rate limiting
            time.sleep(1)
            
        return results
    
    def schedule_post(self, 
                      content: Dict, 
                      media_files: Optional[Dict[str, List[str]]] = None,
                      platforms: Optional[List[str]] = None,
                      custom_personalities: Optional[Dict[str, str]] = None,
                      post_time: datetime = None) -> Dict:
        """
        Schedule a post for later publication.
        
        Args:
            content: Content dict with headline, intro, body, conclusion
            media_files: Dict mapping platform to media file paths
            platforms: List of platforms to post to (uses all available if None)
            custom_personalities: Override default personalities by platform
            post_time: When to publish the post (None for immediate posting)
            
        Returns:
            Dict with schedule confirmation or immediate results if post_time is None
        """
        if not post_time or post_time <= datetime.now():
            # Post immediately
            return self.post_to_platforms(content, media_files, platforms, custom_personalities)
        
        # Convert content dict to PostContent model
        post_content = self._convert_to_post_content(content)
        
        # Create schedule options
        schedule_options = ScheduleOptions(
            post_time=post_time,
            platforms=platforms or list(self.platforms.keys()),
            content=post_content,
            media_files=media_files,
            personalities=custom_personalities
        )
        
        # TODO: Implement scheduling logic with a task queue or database
        # For now, serialize to JSON and return a placeholder confirmation
        schedule_file = f"scheduled_posts/{int(time.time())}.json"
        os.makedirs("scheduled_posts", exist_ok=True)
        
        with open(schedule_file, 'w') as f:
            # Convert to dict for JSON serialization
            schedule_dict = schedule_options.dict()
            # Convert datetime to string
            schedule_dict['post_time'] = schedule_options.post_time.isoformat()
            json.dump(schedule_dict, f, indent=2)
        
        return {
            "scheduled": True,
            "post_time": post_time.isoformat(),
            "platforms": platforms or list(self.platforms.keys()),
            "schedule_file": schedule_file
        } 