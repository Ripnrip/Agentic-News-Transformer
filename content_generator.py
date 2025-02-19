from typing import List, Dict
from openai import OpenAI
import os
from database_agent import DatabaseAgent
import json
from textwrap import dedent
from datetime import datetime

class ContentGenerationAgent:
    """Agent for generating accessible and inclusive tech content."""
    
    def __init__(self, db_agent: DatabaseAgent):
        self.db_agent = db_agent
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
    def _build_article_context(self, similar_articles: List[Dict]) -> str:
        """Build context from similar articles."""
        context = []
        for article in similar_articles:
            context.append(f"""
Title: {article['article']['title']}
Source: {article['article']['source']}
Content: {article['chunk']}
---""")
        return "\n".join(context)
    
    def _generate_content(self, context: str, topic: str, similar_articles: List[Dict]) -> Dict[str, str]:
        """Generate article content using GPT-4 and include metadata."""
        prompt = dedent(f"""
            Based on the following articles about {topic}, create a comprehensive blog post.
            Make it engaging and accessible while maintaining technical accuracy. The tone should be a sexy girl news reporter seducing the audience.

            Source Articles:
            {context}

            Generate content within these length limits:
            - Headline: 50-100 characters
            - Introduction: 150-200 words
            - Main body: 800-1000 words
            - Conclusion: 100-150 words

            Format the response as a valid JSON object with these exact keys:
            {{
                "headline": "Your headline here",
                "intro": "Your introduction here",
                "body": "Your main content here",
                "conclusion": "Your conclusion here"
            }}

            Ensure the response is properly formatted JSON with escaped quotes and newlines.
        """).strip()
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a skilled tech writer creating engaging content."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=7000
        )
        
        try:
            content = json.loads(response.choices[0].message.content)
            
            # Add metadata with safer access to fields
            metadata = {
                "generated_date": datetime.now().isoformat(),
                "topic": topic,
                "sources": [
                    {
                        "title": article.get('article', {}).get('title', ''),
                        "url": article.get('article', {}).get('link', ''),
                        "source": article.get('article', {}).get('source', ''),
                        "published_date": article.get('article', {}).get('published_date', ''),
                        "article_id": article.get('article', {}).get('id', ''),
                        "chunk": article.get('chunk', ''),
                        "similarity_score": article.get('similarity_score', 0.0)
                    }
                    for article in similar_articles
                ],
                "hashtags": self._generate_hashtags(topic, content['headline']),
                "word_counts": {
                    "intro": len(content['intro'].split()),
                    "body": len(content['body'].split()),
                    "conclusion": len(content['conclusion'].split())
                }
            }
            
            return {**content, "metadata": metadata}
        except json.JSONDecodeError as e:
            print(f"Error parsing GPT response: {e}")
            return {
                "headline": "Error parsing response",
                "intro": response.choices[0].message.content[:200],
                "body": response.choices[0].message.content[200:1800],
                "conclusion": response.choices[0].message.content[1800:]
            }
    
    def _generate_hashtags(self, topic: str, headline: str) -> List[str]:
        """Generate relevant hashtags from topic and headline."""
        prompt = dedent(f"""
            Generate 5-7 relevant hashtags for a tech article with:
            Topic: {topic}
            Headline: {headline}
            
            Format as JSON array of strings. Make hashtags trendy and relevant.
        """)
        
        response = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        
        try:
            return json.loads(response.choices[0].message.content)
        except:
            return [f"#{topic.replace(' ', '')}", "#AI", "#Tech"]
    
    def generate_article(self, topic: str) -> Dict[str, str]:
        """Generate clear, accessible tech content."""
        similar_articles = self.db_agent.search_similar(topic)
        context = self._build_article_context(similar_articles)
        return self._generate_content(context, topic, similar_articles) 