"""Agent for generating accessible and inclusive tech content using Pydantic AI."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import os
import json
from datetime import datetime
from openai import OpenAI
import streamlit as st

# Define model types
class SimilarArticle(BaseModel):
    """Model for similar article data."""
    title: str
    content: str
    source: Optional[str] = None
    url: Optional[str] = None
    similarity_score: float

class GenerationRequest(BaseModel):
    """Model for content generation request."""
    topic: str
    similar_articles: List[SimilarArticle] = Field(default_factory=list)
    tone: str = "informative"
    target_audience: str = "general"
    word_count: int = 800

class GeneratedContent(BaseModel):
    """Model for generated content."""
    headline: str
    intro: str
    body: str
    conclusion: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ArticleRequest(BaseModel):
    """Request model for article generation."""
    topic: str = Field(description="Topic to generate article about")
    tone: str = Field(default="professional", description="Tone of the article")
    length: str = Field(default="medium", description="Length of the article")

class ArticleResult(BaseModel):
    """Result model for article generation."""
    title: str = Field(description="Generated article title")
    content: str = Field(description="Generated article content")
    summary: str = Field(description="Brief summary of the article")
    keywords: list = Field(description="Keywords for the article")

class ContentGenerationAgent:
    """Agent for generating content."""
    
    def __init__(self, db_agent):
        """Initialize the content generation agent."""
        # Initialize OpenAI client
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db_agent = db_agent # Store the database agent
        

    def generate_article_content(self, request: ArticleRequest) -> ArticleResult:
        """Generate article content based on the request."""
        try:
            st.write("🤖 Creating script prompt...")
            st.write("📝 Input topic length:", len(request.topic), "characters")
            
            # Create a preview of the topic
            topic_preview = request.topic[:500] + "..." if len(request.topic) > 500 else request.topic
            with st.expander("📄 Input Topic Preview"):
                st.markdown(topic_preview)
            
            # Truncate extremely long inputs to prevent token limit issues
            max_chars = 4000
            truncated_topic = request.topic
            if len(request.topic) > max_chars:
                st.warning(f"⚠️ Topic too long ({len(request.topic)} chars). Truncating to {max_chars} chars to fit model context.")
                truncated_topic = request.topic[:max_chars] + "... [truncated for length]"
            
            # Create prompt for 30-second script
            prompt = f"""
            Create a 30-second news script (approximately 75 words) about this topic:
            {truncated_topic}
            
            Requirements:
            1. Must be exactly 30 seconds when read at a natural pace
            2. Use a {request.tone} tone
            3. Focus on the key points
            4. Be engaging and conversational
            5. Use clear language suitable for speaking
            6. Include a clear opening and closing
            
            Structure your response in this exact format:
            TITLE: <brief title>
            SCRIPT: <the complete 30-second script>
            SUMMARY: <one-line summary>
            KEYWORDS: <comma-separated keywords>
            """
            
            st.write("🎯 Generating script with GPT-4...")
            st.write("⏳ This may take a few moments...")
            
            # Select model based on input length - use more efficient model for longer texts
            model = "gpt-3.5-turbo" if len(truncated_topic) > 2000 else "gpt-4"
            st.write(f"Using model: {model}")
            
            # Generate content with OpenAI
            try:
                response = self.client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    max_tokens=1000  # Limit response length
                )
            except Exception as api_error:
                st.error(f"API Error: {str(api_error)}")
                # Fall back to gpt-3.5-turbo if gpt-4 fails
                if model == "gpt-4":
                    st.write("Falling back to GPT-3.5-Turbo...")
                    response = self.client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        temperature=0.7,
                        max_tokens=1000
                    )
                else:
                    raise api_error
            
            # Parse response
            response_text = response.choices[0].message.content
            st.write("✨ Processing AI response...")
            
            with st.expander("🔍 Raw AI Response"):
                st.code(response_text, language="text")
            
            # Parse the response text
            lines = response_text.split('\n')
            content_dict = {}
            current_key = None
            current_value = []
            
            st.write("🔄 Parsing response sections...")
            
            for line in lines:
                line = line.strip()
                if line.startswith('TITLE:'):
                    if current_key and current_key != 'keywords':
                        content_dict[current_key] = '\n'.join(current_value).strip()
                    current_key = 'title'
                    current_value = [line.replace('TITLE:', '').strip()]
                    st.write("📌 Found title section")
                elif line.startswith('SCRIPT:'):
                    if current_key and current_key != 'keywords':
                        content_dict[current_key] = '\n'.join(current_value).strip()
                    current_key = 'content'
                    current_value = [line.replace('SCRIPT:', '').strip()]
                    st.write("📜 Found script section")
                elif line.startswith('SUMMARY:'):
                    if current_key and current_key != 'keywords':
                        content_dict[current_key] = '\n'.join(current_value).strip()
                    current_key = 'summary'
                    current_value = [line.replace('SUMMARY:', '').strip()]
                    st.write("📋 Found summary section")
                elif line.startswith('KEYWORDS:'):
                    if current_key and current_key != 'keywords':
                        content_dict[current_key] = '\n'.join(current_value).strip()
                    current_key = 'keywords'
                    keywords_text = line.replace('KEYWORDS:', '').strip()
                    content_dict[current_key] = [k.strip() for k in keywords_text.split(',')]
                    st.write("🏷️ Found keywords section")
                elif line and current_key:
                    current_value.append(line)
            
            if current_key:
                if current_key != 'keywords':
                    content_dict[current_key] = '\n'.join(current_value).strip()
            
            # Validate required fields
            required_fields = ['title', 'content', 'summary', 'keywords']
            missing_fields = [field for field in required_fields if field not in content_dict]
            
            if missing_fields:
                st.error(f"❌ Missing required fields in AI response: {', '.join(missing_fields)}")
                st.error("Response structure was not as expected. Here's what we got:")
                for key, value in content_dict.items():
                    st.write(f"✓ Found {key}")
                st.code(response_text, language="text")
                return None
            
            # Show parsed content
            with st.expander("🎯 Parsed Content"):
                st.write("**Title:**", content_dict['title'])
                st.write("**Script:**", content_dict['content'])
                st.write("**Summary:**", content_dict['summary'])
                st.write("**Keywords:**", ", ".join(content_dict['keywords']))
            
            st.success("✅ Script generated successfully!")
            
            return ArticleResult(
                title=content_dict.get("title", "News Script"),
                content=content_dict.get("content", ""),
                summary=content_dict.get("summary", ""),
                keywords=content_dict.get("keywords", [])
            )
            
        except Exception as e:
            st.error(f"❌ Error generating script: {str(e)}")
            st.error("Full error details:")
            st.exception(e)
            return None

    def generate_hashtags(self, content: str) -> list:
        """Generate relevant hashtags for the content."""
        try:
            st.write("🏷️ Generating hashtags...")
            
            # Create prompt for hashtags
            prompt = """
            Generate 5 relevant hashtags for this content.
            Format your response as:
            HASHTAGS: #tag1, #tag2, #tag3, #tag4, #tag5
            """
            
            # Generate hashtags with OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": content},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            hashtags_text = response_text.replace('HASHTAGS:', '').strip()
            hashtags = [tag.strip() for tag in hashtags_text.split(',') if tag.strip()]
            
            st.write("✅ Generated hashtags:", ", ".join(hashtags))
            return hashtags
            
        except Exception as e:
            st.error(f"❌ Error generating hashtags: {str(e)}")
            st.exception(e)
            return []

    def generate_article(self, topic: str, db_search_results=None) -> Dict[str, Any]:
        """Generate an article about the given topic."""
        # Convert search results to SimilarArticle objects
        similar_articles = []
        if db_search_results:
            for result in db_search_results:
                similar_articles.append(SimilarArticle(
                    title=result.article.title,
                    content=result.chunk,
                    source=result.article.source,
                    url=result.article.link,
                    similarity_score=result.similarity_score
                ))
        
        # Build context from similar articles - include more content
        context_text = "\n\n".join([
            f"Article: {article.title}\nSource: {article.source or 'Unknown'}\nURL: {article.url or 'Unknown'}\n"
            f"Content: {article.content}\n"
            for article in similar_articles
        ])
        
        # Create prompt
        prompt = f"""
        You are an AI summarizer that accurately condenses articles while preserving all key information. Your job is to create a faithful summary of the EXACT article content provided below - do not include any information not present in the original article.

        INSTRUCTIONS:
        1. ONLY summarize the SPECIFIC article content provided in the REFERENCE CONTEXT
        2. DO NOT add any information, examples, or details not explicitly mentioned in the article
        3. DO NOT make generalizations about the topic that aren't directly from the article
        4. Include ALL key points, quotes, statistics, and factual information from the source
        5. Maintain the same perspective and tone as the original article
        6. The headline must directly reflect the main topic of the specific article
        
        REFERENCE CONTEXT:
        {context_text}
        
        FORMAT:
        Return a JSON object with the following structure:
        {{
            "headline": "A headline that directly reflects the specific article content",
            "intro": "Brief introduction summarizing the main point of the article",
            "body": "Detailed summary covering all key points from the article",
            "conclusion": "Brief conclusion based only on what's in the article",
            "metadata": {{
                "topic": "{topic}",
                "word_count": <actual_word_count>,
                "source": "<name of original publication>",
                "published_date": "<date from article if available>",
                "hashtags": ["#relevanthashtag1", "#relevanthashtag2"],
                "generated_date": "<current_date>"
            }}
        }}
        """
        
        # Generate content with OpenAI directly
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3  # Lowered temperature for more factual output
        )
        
        # Parse response JSON
        try:
            content_json = json.loads(response.choices[0].message.content)
            
            # Add generated date if not present
            if "metadata" in content_json and "generated_date" not in content_json["metadata"]:
                content_json["metadata"]["generated_date"] = datetime.now().isoformat()
            
            # Add sources metadata
            if "metadata" in content_json:
                content_json["metadata"]["sources"] = [
                    {"title": a.title, "source": a.source, "url": a.url, "score": a.similarity_score}
                    for a in similar_articles
                ]
            
            return content_json
        except Exception as e:
            raise ValueError(f"Failed to parse generated content: {str(e)}")

    def generate_article_from_direct_sources(self, topic: str, similar_articles: List[SimilarArticle]) -> Dict[str, Any]:
        """Generate an article summary directly from provided articles without database search."""
        # Build context from the provided articles
        context_text = "\n\n".join([
            f"Article: {article.title}\nSource: {article.source or 'Unknown'}\nURL: {article.url or 'Unknown'}\n"
            f"Content: {article.content}\n"
            for article in similar_articles
        ])
        
        # Create prompt
        prompt = f"""
        You are an AI summarizer that accurately condenses articles while preserving all key information. Your job is to create a faithful summary of the EXACT article content provided below - do not include any information not present in the original article.

        INSTRUCTIONS:
        1. ONLY summarize the SPECIFIC article content provided in the REFERENCE CONTEXT
        2. DO NOT add any information, examples, or details not explicitly mentioned in the article
        3. DO NOT make generalizations about the topic that aren't directly from the article
        4. Include ALL key points, quotes, statistics, and factual information from the source
        5. Maintain the same perspective and tone as the original article
        6. The headline must directly reflect the main topic of the specific article
        
        REFERENCE CONTEXT:
        {context_text}
        
        FORMAT:
        Return a JSON object with the following structure:
        {{
            "headline": "A headline that directly reflects the specific article content",
            "intro": "Brief introduction summarizing the main point of the article",
            "body": "Detailed summary covering all key points from the article",
            "conclusion": "Brief conclusion based only on what's in the article",
            "metadata": {{
                "topic": "{topic}",
                "word_count": <actual_word_count>,
                "source": "<name of original publication>",
                "published_date": "<date from article if available>",
                "hashtags": ["#relevanthashtag1", "#relevanthashtag2"],
                "generated_date": "<current_date>"
            }}
        }}
        """
        
        # Generate content with OpenAI directly
        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.3  # Lowered temperature for more factual output
        )
        
        # Parse response JSON
        try:
            content_json = json.loads(response.choices[0].message.content)
            
            # Add generated date if not present
            if "metadata" in content_json and "generated_date" not in content_json["metadata"]:
                content_json["metadata"]["generated_date"] = datetime.now().isoformat()
            
            # Add sources metadata
            if "metadata" in content_json:
                content_json["metadata"]["sources"] = [
                    {"title": a.title, "source": a.source, "url": a.url, "score": a.similarity_score}
                    for a in similar_articles
                ]
            
            return content_json
        except Exception as e:
            raise ValueError(f"Failed to parse generated content: {str(e)}") 