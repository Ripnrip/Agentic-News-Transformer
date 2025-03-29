# Netlify Deployment for Agentic Content Transformer

This directory contains files for deploying a landing page for the Agentic Content Transformer to Netlify.

## What's Included

- `public/` - Static files for the landing page
- `deploy.sh` - Script to deploy to Netlify
- `README.md` - This file

## Deployment Instructions

### Option 1: Using the Deployment Script

The easiest way to deploy is using our deployment script:

```bash
# Make the script executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
```

This will:
1. Install netlify-cli if needed
2. Log you in to Netlify
3. Deploy the site to production

### Option 2: Manual Deployment

If you prefer to deploy manually:

1. Install the Netlify CLI:
   ```bash
   npm install -g netlify-cli
   ```

2. Log in to Netlify:
   ```bash
   netlify login
   ```

3. Initialize your Netlify site (first time only):
   ```bash
   netlify init
   ```

4. Deploy to production:
   ```bash
   netlify deploy --prod
   ```

## Customizing Your Landing Page

To customize the landing page:

1. Edit `public/index.html` to change content, styles, and links
2. Update the URLs in the HTML file to point to your actual Streamlit app
3. Add any additional static assets (images, CSS, JS) to the `public/` directory

## Connecting to Your Streamlit App

The landing page is designed to link to your Streamlit app. Make sure to update these URLs:

1. In `index.html`:
   - Update the "Launch App" button URL
   - Update the GitHub repository URL

2. In `netlify.toml`:
   - Update the redirect URLs to point to your actual Streamlit app
   - Update the API proxy URL if you're using it

## Adding a Custom Domain

Once deployed, you can add a custom domain through the Netlify dashboard:

1. Go to your site settings in Netlify
2. Navigate to "Domain settings"
3. Click "Add custom domain"
4. Follow the instructions to set up DNS records

## Need Help?

If you encounter issues:

1. Check the [Netlify documentation](https://docs.netlify.com/)
2. Visit the [Streamlit deployment guide](https://docs.streamlit.io/streamlit-community-cloud) 