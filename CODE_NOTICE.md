# Code Access Notice

## Repository Status

This repository contains only the run scripts, documentation, and supporting files for the Agentic Content Transformer project. The full source code was excluded due to GitHub's secret scanning detecting potential sensitive information in the commit history.

## How to Access the Full Code

The complete codebase is available locally on the original developer's machine. For legitimate collaborators who need access to the full codebase, please contact the repository owner directly.

## Files Needed for Full Functionality

The following Python files should be included for the application to function properly:

- `app.py` - Main application entry point
- `news_to_avatar.py` - News-to-Avatar processing logic
- `agents.py` - Agent definitions
- `audio_generator.py` - Audio generation functionality
- `avatar_generator.py` - Avatar generation functionality
- `content_generator.py` - Content generation functionality
- `database_agent.py` - Database interaction
- `env_validator.py` - Environment validation
- `models.py` - Data models
- `social_media_agent.py` - Social media integration

## Getting Started

1. Clone this repository
2. Obtain the full source code from the repository owner
3. Set up your environment variables (see .env.example)
4. Run the application using one of the provided scripts:
   - `./run-local.sh` - For local development
   - `./run-unified.sh` - For the unified app interface
   - `./run-docker.sh` - For Docker-based deployment

## Contributing

Please make sure to sanitize any API keys or sensitive information before committing code to this repository. 