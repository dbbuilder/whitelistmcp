#!/bin/bash
# Git setup commands for awswhitelist2

# Initialize git repository
git init

# Add all files
git add .

# Initial commit
git commit -m "Initial commit: Python MCP server for AWS IP whitelisting"

# Add remote repository (replace [your-username] with your GitHub username)
# git remote add origin https://github.com/[your-username]/awswhitelist2.git

# Push to GitHub
# git push -u origin main

echo "Git repository initialized. Run the following commands to connect to GitHub:"
echo "1. Create a private repository named 'awswhitelist2' on GitHub"
echo "2. git remote add origin https://github.com/[your-username]/awswhitelist2.git"
echo "3. git push -u origin main"