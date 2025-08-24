#!/bin/bash

# HVAC Scraper Startup Script
# This script allows you to easily start the application with custom credentials

echo "🔐 HVAC Business Scraper - Secure Startup"
echo "=========================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Set default credentials if not provided
if [ -z "$LOGIN_USERNAME" ]; then
    export LOGIN_USERNAME="admin"
fi

if [ -z "$LOGIN_PASSWORD" ]; then
    export LOGIN_PASSWORD="hvac2024!"
fi

if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY="hvac-scraper-$(date +%s)-$(openssl rand -hex 16)"
fi

# Load .env file if it exists
if [ -f ".env" ]; then
    echo "Loading configuration from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

echo ""
echo "🚀 Starting HVAC Scraper..."
echo "📍 URL: http://localhost:5000"
echo "👤 Username: $LOGIN_USERNAME"
echo "🔑 Password: $LOGIN_PASSWORD"
echo ""
echo "💡 To change credentials:"
echo "   LOGIN_USERNAME=myuser LOGIN_PASSWORD=mypass ./start.sh"
echo "   Or create a .env file with your settings"
echo ""

# Start the application
python src/main.py

