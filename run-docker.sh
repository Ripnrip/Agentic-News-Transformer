#!/bin/bash

# Stop any existing container with the same name
docker stop agentic-transformer || true
docker rm agentic-transformer || true

# Check for .env file and load it if it exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file"
  export $(grep -v '^#' .env | xargs)
fi

# Check if the OpenAI API key is available
if [ -z "$OPENAI_API_KEY" ]; then
  # Prompt for OpenAI API key if not found
  echo "Enter your OpenAI API key:"
  read -s OPENAI_API_KEY
  if [ -z "$OPENAI_API_KEY" ]; then
    echo "No API key provided. Exiting."
    exit 1
  fi
  export OPENAI_API_KEY=$OPENAI_API_KEY
else
  echo "Using existing OpenAI API key"
fi

# Set environment variables placeholders - use your own keys in production
if [ -z "$ELEVENLABS_API_KEY" ]; then
  export ELEVENLABS_API_KEY="placeholder_key"
fi

if [ -z "$ELEVENLABS_VOICE_ID" ]; then
  export ELEVENLABS_VOICE_ID="placeholder_id"
fi

if [ -z "$SYNC_SO_API_KEY" ]; then
  export SYNC_SO_API_KEY="placeholder_key"
fi

if [ -z "$AWS_ACCESS_KEY_ID" ]; then
  export AWS_ACCESS_KEY_ID="placeholder_id"
fi

if [ -z "$AWS_SECRET_ACCESS_KEY" ]; then
  export AWS_SECRET_ACCESS_KEY="placeholder_key"
fi

if [ -z "$AWS_DEFAULT_REGION" ]; then
  export AWS_DEFAULT_REGION="placeholder_region"
fi

export SKIP_CONDA_CHECK=true

# Function to find available port
find_available_port() {
  local port=$1
  while true; do
    if ! nc -z localhost $port &>/dev/null; then
      echo $port
      return 0
    fi
    port=$((port + 1))
  done
}

# Find an available port
PORT=$(find_available_port 8080)
echo "Using port $PORT for Docker container"

# Create and run Docker container with environment variables
docker run -it --rm \
  -p $PORT:8080 \
  -e PORT=8080 \
  -e STREAMLIT_SERVER_PORT=8080 \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ELEVENLABS_API_KEY="$ELEVENLABS_API_KEY" \
  -e ELEVENLABS_VOICE_ID="$ELEVENLABS_VOICE_ID" \
  -e SYNC_SO_API_KEY="$SYNC_SO_API_KEY" \
  -e AWS_ACCESS_KEY_ID="$AWS_ACCESS_KEY_ID" \
  -e AWS_SECRET_ACCESS_KEY="$AWS_SECRET_ACCESS_KEY" \
  -e AWS_DEFAULT_REGION="$AWS_DEFAULT_REGION" \
  -e SKIP_CONDA_CHECK="$SKIP_CONDA_CHECK" \
  gsinghdev/agentic-content-transformer:latest \
  streamlit run app.py --server.port=8080 --server.address=0.0.0.0

echo "Container started. Access the app at http://localhost:$PORT"
echo "Check logs with: docker logs agentic-transformer" 