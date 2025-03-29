# Sync.so Integration Guide

## Overview

This document provides details about integrating the Sync.so API for lip-synced avatar video generation in the Agentic Content Transformer project. We successfully implemented a flexible, reliable pipeline for creating lip-synced videos using public URLs.

## Core Components

1. **Avatar Generation Agent**: Managed in `avatar_generator.py`, handles the core integration with Sync.so API
2. **Test Scripts**: Standalone utilities to test and troubleshoot API integration
3. **URL Management**: Solution for handling audio and video URLs required by Sync.so
4. **Job Management**: System for tracking, monitoring, and retrieving generated videos

## API Configuration

### Endpoint Details

- Base URL: `https://api.sync.so/v2`
- Main endpoints:
  - `/generate`: POST to create a new video generation job
  - `/generate/{id}`: GET to check status of an existing job
- Authentication: `x-api-key` header with API key from environment variable `SYNC_SO_API_KEY`

### Request Format

```json
{
  "model": "lipsync-1.9.0-beta",
  "input": [
    {
      "type": "video",
      "url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/hoe_3_30.mp4"
    },
    {
      "type": "audio",
      "url": "https://vectorverseevolve.s3.us-west-2.amazonaws.com/News_Script_20250329_033235.mp3"
    }
  ],
  "options": {
    "output_format": "mp4",
    "sync_mode": "bounce",
    "fps": 25,
    "output_resolution": [480, 854],
    "active_speaker": true
  }
}
```

## Key Learnings

1. **URL Requirements**: Sync.so requires all input files (both audio and video) to be hosted on publicly accessible URLs. Direct file uploads are not supported.

2. **Aspect Ratio Matters**: For portrait videos, use a 9:16 aspect ratio. We found that 480x854 works well for maintaining proportions. Incorrect aspect ratios lead to stretched or distorted videos.

3. **Job Processing Time**: Video generation can take 1-5 minutes depending on length and complexity. Implementing flexible polling mechanisms helps handle this.

4. **Error Handling**: API responses provide detailed error information, which should be properly handled and displayed to users.

## Successful Implementation

We have two successful video generations stored:

1. **Initial Test**:
   - Job ID: `d0776b3c-62d8-4cd7-a804-cbe1cdba1d43`
   - Video URL: [Initial Video (aspect ratio issue)](https://api.sync.so/v2/generations/d0776b3c-62d8-4cd7-a804-cbe1cdba1d43/result?token=e0715e7e-1df6-4beb-b548-6cb370c3e3de)
   - Notes: First successful integration, but had stretched aspect ratio

2. **Fixed Aspect Ratio**:
   - Job ID: `7b50995e-df61-4940-ba49-dcf7615b5301`
   - Video URL: [Fixed Video (correct aspect ratio)](https://api.sync.so/v2/generations/7b50995e-df61-4940-ba49-dcf7615b5301/result?token=bbb5ed1e-86f7-4d7b-b2a4-5f9e0aae686d)
   - Resolution: 480x854 (proper 9:16 ratio)
   - Notes: Corrected aspect ratio for better visual appearance

## Test Scripts

### 1. Basic API Test

`test_sync_direct.py` validates basic connectivity to the Sync.so API using public URLs.

### 2. Aspect Ratio Fix

`fix_aspect_ratio.py` demonstrates proper aspect ratio settings for portrait videos.

### 3. Job Status Checker

`check_sync_job.py` provides a command-line tool to check status of any job with optional indefinite polling:

```
python check_sync_job.py <job_id> --poll --interval 10
```

## Integration Tips

1. **Always Host Files Publicly**: Ensure all audio and video files are hosted on a public service like AWS S3.

2. **Consider AWS S3 Integration**: For production use, implement direct S3 upload functionality in the app.

3. **Implement Webhook Support**: For better notification of job completion, implement webhook support provided by Sync.so.

4. **Set Appropriate Timeouts**: Some jobs may take 5+ minutes to complete. Implement appropriate polling and timeout strategies.

5. **Manage API Keys Securely**: Store the `SYNC_SO_API_KEY` in environment variables or secure storage.

## Known Issues and Solutions

| Issue | Solution |
|-------|----------|
| File validation errors | Skip URL validation for remote files |
| Stretched videos | Use 9:16 aspect ratio (480x854) for portrait videos |
| Long processing times | Implement indefinite polling with clear status updates |
| API response format | Ensure field access matches current API version |

## Future Improvements

1. **Direct S3 Upload**: Implement automatic uploading of audio files to AWS S3
2. **Webhook Support**: Add webhook URL for job completion notifications
3. **Caching**: Implement caching of generated videos to reduce API calls
4. **Multiple Avatar Support**: Expand the avatar selection with more options
5. **Customizable Output Settings**: Allow user customization of output resolution, FPS, etc.

## Resources

- [Sync.so API Documentation](https://docs.sync.so/api-reference/endpoint/generate/post-generate)
- [AWS S3 Python SDK (boto3)](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [Streamlit Documentation](https://docs.streamlit.io/) for UI components

---

*This documentation reflects the status of the Sync.so integration as of March 29, 2025.* 