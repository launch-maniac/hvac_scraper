#!/bin/bash
set -e

echo "🔧 Setting up HVAC Scraper on server..."

# Create directories
mkdir -p data reports logs

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

# Start the application
echo "🚀 Starting HVAC Scraper..."
docker-compose -f docker-compose.production.yml up -d --build

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 30

# Test if service is running
if curl -f http://localhost:5001/login > /dev/null 2>&1; then
    echo "✅ Service is running on port 5001"
else
    echo "❌ Service failed to start. Checking logs..."
    docker-compose -f docker-compose.production.yml logs
    exit 1
fi

# Setup Nginx
echo "🌐 Setting up Nginx..."
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt update
    apt install -y nginx
fi

# Copy nginx configuration
cp nginx-hvac.conf /etc/nginx/sites-available/hvac-scraper
ln -sf /etc/nginx/sites-available/hvac-scraper /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

# Setup SSL certificate
echo "🔒 Setting up SSL certificate..."
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Get SSL certificate
certbot --nginx -d listbuilder.mopsy.io --non-interactive --agree-tos --email admin@mopsy.io

# Reload nginx
systemctl reload nginx

echo "🎉 HVAC Scraper deployed successfully!"
echo "🌐 Access at: https://listbuilder.mopsy.io"
echo "👤 Username: Jake"
echo "🔑 Password: JakeWhitbeck"
