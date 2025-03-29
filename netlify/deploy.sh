#!/bin/bash

# Exit on error
set -e

# Check if netlify-cli is installed
if ! command -v netlify &> /dev/null; then
    echo "Installing netlify-cli..."
    npm install -g netlify-cli
fi

# Login to Netlify (if not already logged in)
echo "Please login to Netlify if prompted..."
netlify status || netlify login

# Deploy to Netlify
echo "Deploying to Netlify..."
netlify deploy --prod

echo "Deployment complete! Your site should be live now."
echo "You can visit your site at the URL provided above." 