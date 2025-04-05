"""Agent for generating accessible and inclusive tech content using Pydantic AI."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
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
        
        # Create the agent
        self.agent = Agent(
            "openai:gpt-4",  # Using OpenAI for content generation
            deps_type=dict,  # Article request will be passed as dependency
            result_type=ArticleResult,
            system_prompt="Generate engaging and informative articles on various topics."
        )

    def generate_article_content(self, request: ArticleRequest) -> ArticleResult:
        """Generate article content based on the request."""
        try:
            st.write("🤖 Creating script prompt...")
            st.write("📝 Input topic length:", len(request.topic), "characters")
            
            # Create a preview of the topic
            topic_preview = request.topic[:500] + "..." if len(request.topic) > 500 else request.topic
            with st.expander("📄 Input Topic Preview"):
                st.markdown(topic_preview)
            
            # Create prompt for 30-second script
            prompt = f"""
            Create a 30-second news script (approximately 75 words) about this topic:
            {request.topic}
            
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
            
            # Generate content with OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            
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
        
        # Build context from similar articles
        context_text = "\n\n".join([
            f"Article: {article.title}\nSource: {article.source or 'Unknown'}\n"
            f"Content: {article.content[:500]}...\n"
            for article in similar_articles
        ])
        
        # Create prompt
        prompt = f"""
        Generate a clear, accessible article about "{topic}" in an informative tone for a general audience.
        
        The article should be approximately 800 words and include:
        1. An attention-grabbing headline
        2. An engaging introduction
        3. Informative body content 
        4. A concise conclusion
        
        REFERENCE CONTEXT:
        {context_text}
        
        FORMAT:
        Return a JSON object with the following structure:
        {{
            "headline": "The headline",
            "intro": "Introduction paragraph",
            "body": "Main content...",
            "conclusion": "Concluding paragraph",
            "metadata": {{
                "topic": "{topic}",
                "word_count": <actual_word_count>,
                "tone": "informative",
                "audience": "general",
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
            temperature=0.7
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