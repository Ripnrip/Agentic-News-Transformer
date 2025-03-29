#!/bin/bash
# Helper script for deploying to Streamlit Cloud

# Exit on error
set -e

# Function to print colored output
print_color() {
  if [ "$2" = "green" ]; then
    echo -e "\033[32m$1\033[0m"
  elif [ "$2" = "red" ]; then
    echo -e "\033[31m$1\033[0m"
  elif [ "$2" = "yellow" ]; then
    echo -e "\033[33m$1\033[0m"
  else
    echo -e "$1"
  fi
}

# Navigate to the project root
cd "$(dirname "$0")/../.."
ROOT_DIR=$(pwd)

print_color "Preparing for Streamlit Cloud deployment..." "green"

# Check for git
if ! command -v git &> /dev/null; then
  print_color "Error: git is not installed. Please install it before continuing." "red"
  exit 1
fi

# Check if we're in a git repository
if [ ! -d ".git" ]; then
  print_color "Initializing Git repository..." "yellow"
  git init
fi

# Ensure .streamlit directory exists
if [ ! -d ".streamlit" ]; then
  print_color "Creating .streamlit directory..." "yellow"
  mkdir -p .streamlit
fi

# Check for secrets.toml example
if [ ! -f ".streamlit/secrets.toml.example" ]; then
  print_color "Error: .streamlit/secrets.toml.example not found." "red"
  exit 1
fi

# Remind about secrets
print_color "IMPORTANT: Before deploying to Streamlit Cloud, make sure to:" "yellow"
print_color "1. Copy .streamlit/secrets.toml.example to .streamlit/secrets.toml and fill in your API keys locally" "yellow"
print_color "2. Add all these secrets in the Streamlit Cloud dashboard after connecting your GitHub repo" "yellow"

# Check if the repository has a remote
if ! git remote -v | grep -q "origin"; then
  print_color "No remote repository found. Please add one with:" "yellow"
  print_color "git remote add origin https://github.com/yourusername/your-repo.git" "yellow"
  
  # Ask for the repository URL
  read -p "Enter your GitHub repository URL (or press Enter to skip): " repo_url
  
  if [ ! -z "$repo_url" ]; then
    git remote add origin "$repo_url"
    print_color "Remote repository added!" "green"
  else
    print_color "Skipping remote repository setup." "yellow"
  fi
fi

# Offer to commit changes
print_color "Would you like to commit your changes?" "yellow"
read -p "Enter y/n: " commit_choice

if [ "$commit_choice" = "y" ] || [ "$commit_choice" = "Y" ]; then
  # Check git status
  git status
  
  # Add files
  print_color "Adding files to git..." "green"
  git add .
  
  # Commit
  print_color "Committing changes..." "green"
  read -p "Enter commit message: " commit_message
  git commit -m "${commit_message:-'Prepare for Streamlit Cloud deployment'}"
  
  # Offer to push
  print_color "Would you like to push to GitHub now?" "yellow"
  read -p "Enter y/n: " push_choice
  
  if [ "$push_choice" = "y" ] || [ "$push_choice" = "Y" ]; then
    print_color "Pushing to GitHub..." "green"
    git push -u origin main || git push -u origin master
    
    print_color "✅ Changes pushed to GitHub!" "green"
    print_color "Now go to https://streamlit.io/cloud to deploy your app." "green"
  else
    print_color "You can push later with 'git push -u origin main'" "yellow"
  fi
else
  print_color "Skipping git commit. You can commit later with 'git commit -m \"Your message\"'" "yellow"
fi

print_color "Streamlit Cloud deployment preparation complete!" "green"
print_color "Visit https://streamlit.io/cloud to connect your GitHub repository and deploy." "green" 