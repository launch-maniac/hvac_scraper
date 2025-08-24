#!/bin/bash

# HVAC Scraper - Hetzner Deployment Script for Jake
# Simplified deployment to Hetzner server

set -e

echo "🚀 HVAC Scraper - Hetzner Deployment for Jake"
echo "=============================================="
echo "Server: 5.78.125.147 (no-code.mopsy.io)"
echo "Username: Jake"
echo "Password: JakeWhitbeck"
echo

# Check if we're in the right directory
if [ ! -f "src/main.py" ]; then
    echo "❌ Please run this script from the hvac_scraper_api directory"
    exit 1
fi

# Configuration
SERVER_IP="5.78.125.147"
DOMAIN="hvac.mopsy.io"
PORT="5001"
USERNAME="Jake"
PASSWORD="JakeWhitbeck"

echo "📋 Configuration:"
echo "   Server: $SERVER_IP"
echo "   Domain: $DOMAIN"
echo "   Port: $PORT"
echo "   Username: $USERNAME"
echo

# Create environment file
cat > .env << EOF
SECRET_KEY=$(openssl rand -hex 32)
LOGIN_USERNAME=$USERNAME
LOGIN_PASSWORD=$PASSWORD
SESSION_TIMEOUT_HOURS=8
DEBUG=False
HOST=0.0.0.0
PORT=5000
EOF

# Create production docker-compose
cat > docker-compose.production.yml << EOF
version: '3.8'

services:
  hvac-scraper:
    build: .
    container_name: hvac-scraper
    restart: unless-stopped
    ports:
      - "$PORT:5000"
    env_file:
      - .env
    volumes:
      - ./data:/app/src/database
      - ./reports:/app/reports
      - ./logs:/app/logs
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/login"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - hvac-network

networks:
  hvac-network:
    driver: bridge
EOF

# Create nginx configuration
cat > nginx-hvac.conf << EOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL configuration (will be handled by certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Main application
    location / {
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Create installation script for server
cat > install-on-server.sh << 'EOF'
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
certbot --nginx -d hvac.mopsy.io --non-interactive --agree-tos --email admin@mopsy.io

# Reload nginx
systemctl reload nginx

echo "🎉 HVAC Scraper deployed successfully!"
echo "🌐 Access at: https://hvac.mopsy.io"
echo "👤 Username: Jake"
echo "🔑 Password: JakeWhitbeck"
EOF

chmod +x install-on-server.sh

echo "📦 Files prepared for deployment!"
echo
echo "📋 Manual Deployment Steps:"
echo "=================================="
echo
echo "1. Upload these files to your Hetzner server at /opt/hvac-scraper/:"
echo "   - All files in this directory"
echo "   - Use Hetzner console file manager"
echo
echo "2. SSH into your server and run:"
echo "   cd /opt/hvac-scraper"
echo "   chmod +x install-on-server.sh"
echo "   ./install-on-server.sh"
echo
echo "3. Your HVAC scraper will be available at:"
echo "   🌐 https://hvac.mopsy.io"
echo "   👤 Username: Jake"
echo "   🔑 Password: JakeWhitbeck"
echo
echo "📁 Files ready for upload:"
echo "   ✅ docker-compose.production.yml"
echo "   ✅ nginx-hvac.conf"
echo "   ✅ install-on-server.sh"
echo "   ✅ .env (with Jake's credentials)"
echo "   ✅ All source code files"
echo
echo "🎯 Ready for deployment to your Hetzner server!"

