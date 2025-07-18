# Changelog

All notable changes to the Agentic News Transformer project will be documented in this file.

## [2025-07-18] - Video Generation Pipeline Complete

### Added
- **Complete AWS S3 Integration**
  - Added AWS credentials configuration in `.env`
  - Implemented automatic audio file upload to S3 bucket `vectorverseevolve`
  - Added video backup to S3 after Sync.so generation
  - S3 bucket configuration with proper prefixes for different content types

- **Enhanced Video Generation Pipeline**
  - Successfully integrated Sync.so API for lip-sync video generation
  - Added proper error handling and status polling for video jobs
  - Implemented video download and S3 backup functionality
  - Added comprehensive job tracking with JSON status files

- **Batch Processing System**
  - Created `batch_10_articles.py` for automated article processing
  - Multi-source article scraping (NewsAPI → RSS → Playwright fallbacks)
  - Complete pipeline from article scraping to video generation
  - Configurable batch sizes (currently set to 3 articles for testing)

### Changed
- **Audio Generation Migration**
  - Migrated from ElevenLabs to OpenAI TTS as primary audio provider
  - Updated voice parameters (`voice_id` → `voice`)
  - Added graceful handling for missing API keys
  - Maintained audio quality with OpenAI's `nova` voice

- **Database Agent Improvements**
  - Added graceful error handling for missing COHERE_API_KEY
  - Enhanced vector store initialization with fallback behavior
  - Improved error messaging for missing dependencies

- **Environment Configuration**
  - Expanded `.env` file with comprehensive AWS and S3 settings
  - Added debugging and logging configuration options
  - Included default asset URLs for consistent avatar usage

### Fixed
- **ContentGenerationAgent Initialization**
  - Fixed missing `db_agent` parameter in agent initialization
  - Resolved Streamlit context warnings in bare mode execution
  - Updated import statements for proper dependency resolution

- **Avatar Generation Issues**
  - Fixed avatar name validation (using "Sexy News Anchor")
  - Resolved 403 Forbidden errors by implementing S3 audio upload
  - Fixed job status polling and response handling

- **API Integration**
  - Updated Sync.so API key to `sk-YEG7hy2IQGyzA1bgDOJtJQ.efoIsDTPb9u3OD_H9SOJ_f1ea30qOhCn`
  - Fixed HTTP 422 errors by ensuring audio files are publicly accessible
  - Improved error handling and debugging output

### Technical Details
- **File Storage Locations:**
  - Audio files: `generated_audio/` (local) + S3 bucket
  - Video files: `generated_videos/` (local) + S3 bucket  
  - Job tracking: `sync_jobs/` (JSON status files)
  - Batch results: `batch_results_YYYYMMDD_HHMMSS.json`

- **API Integrations:**
  - OpenAI GPT-4 for script generation
  - OpenAI TTS for audio synthesis
  - Sync.so API for lip-sync video generation
  - AWS S3 for file storage and hosting
  - Google RSS feeds for article scraping

### Dependencies Updated
- Added `boto3` for AWS S3 integration
- Enhanced `pydantic-ai` usage for agent orchestration
- Maintained `streamlit` compatibility for UI components

### Next Steps
- [ ] Re-integrate ElevenLabs as optional TTS provider
- [ ] Implement TTS provider selection system
- [ ] Create automated cron job for daily article processing
- [ ] Set up automated video posting to social platforms

---

## Previous Versions
*Historical changes were not documented in previous versions*