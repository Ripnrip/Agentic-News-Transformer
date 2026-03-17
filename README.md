<div align="center">

# Agentic News Transformer

### AI Agent-Powered News Ecosystem

<img src="docs/images/agentic-news-transformer-ghibli.png" width="800" alt="Agentic News Transformer — A Ghibli-style illustration of spirit agents in a bustling newsroom" style="border-radius: 16px;">

<br />

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-Agents-1C3C3C?style=for-the-badge)](https://langchain.com)
[![CrewAI](https://img.shields.io/badge/CrewAI-Orchestration-FF6B35?style=for-the-badge)](https://crewai.com)
[![AI Agents](https://img.shields.io/badge/AI_Agents-Autonomous-9E7AFF?style=for-the-badge)](https://en.wikipedia.org/wiki/Intelligent_agent)

*A fully autonomous news ecosystem where AI agents collaborate to discover, analyze, transform, and deliver news content. Multiple specialized agents — researchers, writers, editors, and fact-checkers — work in concert to produce high-quality, contextual news summaries.*

</div>

---

## Overview

The Agentic News Transformer demonstrates the power of multi-agent AI systems applied to real-world content generation. Rather than a single LLM call, it orchestrates a team of specialized AI agents — each with distinct roles, tools, and objectives — that collaborate to produce news content that's researched, written, edited, and fact-checked.

This project showcases advanced agentic patterns: tool use, inter-agent communication, task delegation, memory, and autonomous decision-making.

## Key Features

**Multi-Agent Orchestration** — A crew of specialized agents (Researcher, Writer, Editor, Fact-Checker) collaborate autonomously, each with their own tools and expertise.

**Real-Time News Ingestion** — Agents discover and process news from multiple sources (RSS, APIs, web scraping) with configurable topic filters.

**Contextual Transformation** — Raw news is transformed into audience-specific formats: executive briefs, technical summaries, social posts, and long-form analysis.

**Fact-Checking Pipeline** — Dedicated agent cross-references claims against trusted sources before content is finalized.

**Adaptive Scheduling** — Agents learn which topics trend at which times and adjust their monitoring cadence accordingly.

## Agent Architecture

```
┌────────────────┐     ┌────────────────┐     ┌────────────────┐
│  🔍 Researcher  │────→│  ✍️ Writer      │────→│  📝 Editor     │
│  Discovers news │     │  Drafts content │     │  Refines tone  │
│  Sources & APIs │     │  Structures     │     │  Style guide   │
└────────────────┘     └────────────────┘     └───────┬────────┘
                                                       │
                                                       ↓
                                              ┌────────────────┐
                                              │  ✅ Fact-Checker │
                                              │  Verifies claims │
                                              │  Cross-references│
                                              └───────┬────────┘
                                                       │
                                                       ↓
                                              ┌────────────────┐
                                              │  📤 Publisher    │
                                              │  Formats output  │
                                              │  Multi-channel   │
                                              └────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Agent Framework** | CrewAI, LangChain Agents |
| **LLMs** | GPT-4, Claude 3, Groq (Llama 3) |
| **Tools** | Tavily Search, NewsAPI, BeautifulSoup |
| **Orchestration** | Python async, task queues |
| **Storage** | SQLite (articles), ChromaDB (embeddings) |

## Getting Started

```bash
# Clone the repository
git clone https://github.com/Ripnrip/Agentic-News-Transformer.git
cd Agentic-News-Transformer

# Set up environment
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure API keys
cp .env.example .env
# Add your LLM API keys and news source credentials

# Run the agent crew
python main.py --topics "AI,Technology,Science" --format brief

# Or run with the web dashboard
python dashboard.py
```

## Output Formats

The transformer produces content in multiple formats optimized for different audiences:

**Executive Brief** — 3-5 bullet points with key takeaways and action items.

**Technical Deep-Dive** — Detailed analysis with code references, architecture insights, and technical implications.

**Social Snippet** — Platform-optimized posts for Twitter/X, LinkedIn, and Bluesky.

**Newsletter Section** — Formatted HTML section ready for email newsletter integration.

---

<div align="center">
  <br />
  <p>Built with ✨ by <a href="https://guriboycodes.com"><strong>GuriboyCodes</strong></a></p>
  <sub>Staff Software Engineer — Mobile & AI</sub>
  <br /><br />
  <a href="https://guriboycodes.com">Portfolio</a> · <a href="https://github.com/Ripnrip">GitHub</a> · <a href="https://linkedin.com/in/gurindersingh">LinkedIn</a>
</div>
