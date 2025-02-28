"""Agent for generating accessible and inclusive tech content using Pydantic AI."""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
import os
import json
from datetime import datetime
from openai import OpenAI

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

# Create the agent
content_agent = Agent(
    "openai:gpt-4o",
    deps_type=Any,  # We'll use this for database agent
    result_type=GeneratedContent,
    system_prompt="Generate accessible, informative tech content about AI topics."
)

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@content_agent.tool
def generate_article_content(
    ctx: RunContext[Any],
    request: GenerationRequest
) -> GeneratedContent:
    """
    Generate a complete article based on the request.
    
    Args:
        ctx: Runtime context (contains database agent)
        request: Generation parameters and similar articles
        
    Returns:
        The generated content with metadata
    """
    # Build prompt with context from similar articles
    context_text = "\n\n".join([
        f"Article: {article.title}\nSource: {article.source or 'Unknown'}\n"
        f"Content: {article.content[:500]}...\n"
        for article in request.similar_articles
    ])
    
    prompt = f"""
    Generate a clear, accessible article about "{request.topic}" in a {request.tone} tone for a {request.target_audience} audience.
    
    The article should be approximately {request.word_count} words and include:
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
            "topic": "{request.topic}",
            "word_count": <actual_word_count>,
            "tone": "{request.tone}",
            "audience": "{request.target_audience}",
            "hashtags": ["#relevanthashtag1", "#relevanthashtag2"]
        }}
    }}
    """
    
    # Generate content with OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    
    # Parse response JSON
    try:
        content_json = json.loads(response.choices[0].message.content)
        
        # Create and return structured result
        return GeneratedContent(
            headline=content_json.get("headline", f"Article about {request.topic}"),
            intro=content_json.get("intro", ""),
            body=content_json.get("body", ""),
            conclusion=content_json.get("conclusion", ""),
            metadata=content_json.get("metadata", {
                "topic": request.topic,
                "generated_at": datetime.now().isoformat()
            })
        )
    except Exception as e:
        raise ValueError(f"Failed to parse generated content: {str(e)}")

@content_agent.tool
def generate_hashtags(
    ctx: RunContext[Any],
    topic: str,
    count: int = 5
) -> List[str]:
    """
    Generate relevant hashtags for a topic.
    
    Args:
        ctx: Runtime context
        topic: The topic to generate hashtags for
        count: Number of hashtags to generate
        
    Returns:
        List of hashtag strings
    """
    prompt = f"""
    Generate {count} relevant hashtags for content about "{topic}".
    The hashtags should be relevant to AI and technology trends.
    Return only the hashtags as a JSON array of strings.
    """
    
    response = openai_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.7
    )
    
    try:
        hashtags = json.loads(response.choices[0].message.content).get("hashtags", [])
        return hashtags if hashtags else [f"#{topic.replace(' ', '')}", "#AI", "#Tech"]
    except:
        return [f"#{topic.replace(' ', '')}", "#AI", "#Tech"]

# Simple interface function
def generate_article(topic: str, db_search_results=None) -> Dict[str, Any]:
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
    
    # Create request
    request = GenerationRequest(
        topic=topic,
        similar_articles=similar_articles
    )
    
    # Generate content
    result = content_agent.run_sync(
        "Generate an article about this topic",
        deps=None,
        inputs={"request": request}
    )
    
    if isinstance(result.data, GeneratedContent):
        # Convert to dict for easy serialization
        return result.data.dict()
    
    raise ValueError("Failed to generate content") 