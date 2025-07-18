#!/bin/bash

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
if [ -z "$OPENAI_VOICE" ]; then
  export OPENAI_VOICE="nova"
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

# Always skip conda check
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
PORT=$(find_available_port 8501)
echo "Using port $PORT for Streamlit app"

# Start the app
echo "Starting Streamlit app..."
streamlit run app.py --server.port=$PORT 