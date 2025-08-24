#!/bin/bash

# HVAC Scraper - Deploy to Existing n8n Server
# This script helps you deploy the HVAC scraper alongside your n8n installation

set -e

echo "🚀 HVAC Scraper - n8n Server Deployment"
echo "========================================"

# Configuration
SERVER_IP=""
SERVER_USER="root"
DOMAIN=""
PORT="5001"

# Get user input
read -p "Enter your n8n server IP address: " SERVER_IP
read -p "Enter SSH username [$SERVER_USER]: " INPUT_USER
SERVER_USER=${INPUT_USER:-$SERVER_USER}
read -p "Enter subdomain for HVAC scraper (e.g., hvac.yourdomain.com): " DOMAIN
read -p "Enter port for HVAC scraper [$PORT]: " INPUT_PORT
PORT=${INPUT_PORT:-$PORT}
read -p "Enter admin username [admin]: " USERNAME
USERNAME=${USERNAME:-admin}
read -s -p "Enter admin password: " PASSWORD
echo

# Validate inputs
if [ -z "$SERVER_IP" ]; then
    echo "❌ Server IP is required"
    exit 1
fi

if [ -z "$DOMAIN" ]; then
    echo "❌ Domain is required"
    exit 1
fi

if [ -z "$PASSWORD" ]; then
    echo "❌ Password is required"
    exit 1
fi

echo "📋 Configuration:"
echo "   Server: $SERVER_USER@$SERVER_IP"
echo "   Domain: $DOMAIN"
echo "   Port: $PORT"
echo "   Username: $USERNAME"
echo

read -p "Continue with deployment? (y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Test SSH connection
echo "🔧 Testing SSH connection..."
if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP exit 2>/dev/null; then
    echo "❌ Cannot connect to server. Please check:"
    echo "   - Server IP address"
    echo "   - SSH key authentication"
    echo "   - Server accessibility"
    exit 1
fi

echo "✅ SSH connection successful"

# Create deployment package
echo "📦 Creating deployment package..."
TEMP_DIR=$(mktemp -d)
cp -r . $TEMP_DIR/hvac_scraper_api
cd $TEMP_DIR

# Create environment file
cat > hvac_scraper_api/.env << EOF
SECRET_KEY=$(openssl rand -hex 32)
LOGIN_USERNAME=$USERNAME
LOGIN_PASSWORD=$PASSWORD
SESSION_TIMEOUT_HOURS=8
DEBUG=False
HOST=0.0.0.0
PORT=5000
EOF

# Create production docker-compose
cat > hvac_scraper_api/docker-compose.production.yml << EOF
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
cat > hvac_scraper_api/nginx-hvac.conf << EOF
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
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";

    # Rate limiting for login
    location /login {
        limit_req zone=login burst=3 nodelay;
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Main application
    location / {
        proxy_pass http://localhost:$PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

# Create backup script
cat > hvac_scraper_api/backup.sh << 'EOF'
#!/bin/bash
# Backup script for HVAC Scraper

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/hvac-scraper/backups"

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
cp /opt/hvac-scraper/data/app.db $BACKUP_DIR/app_db_$DATE.db

# Backup reports
tar -czf $BACKUP_DIR/reports_$DATE.tar.gz /opt/hvac-scraper/reports/

# Backup configuration
cp /opt/hvac-scraper/.env $BACKUP_DIR/env_$DATE.backup

# Keep only last 30 days
find $BACKUP_DIR -name "*.db" -mtime +30 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.backup" -mtime +30 -delete

echo "Backup completed: $DATE"
EOF

chmod +x hvac_scraper_api/backup.sh

# Create update script
cat > hvac_scraper_api/update.sh << 'EOF'
#!/bin/bash
# Update script for HVAC Scraper

cd /opt/hvac-scraper

echo "🔄 Updating HVAC Scraper..."

# Pull latest changes (if using git)
# git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.production.yml down
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

echo "✅ Update completed!"
EOF

chmod +x hvac_scraper_api/update.sh

# Create archive
tar -czf hvac_scraper_deployment.tar.gz hvac_scraper_api/

echo "📤 Uploading to server..."
scp hvac_scraper_deployment.tar.gz $SERVER_USER@$SERVER_IP:/tmp/

# Deploy on server
echo "🚀 Deploying on server..."
ssh $SERVER_USER@$SERVER_IP << EOF
set -e

echo "📦 Extracting deployment package..."
cd /opt
tar -xzf /tmp/hvac_scraper_deployment.tar.gz
mv hvac_scraper_api hvac-scraper
cd hvac-scraper

echo "🔧 Setting up directories..."
mkdir -p data reports logs backups

echo "🐳 Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    rm get-docker.sh
fi

if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-\$(uname -s)-\$(uname -m)" -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
fi

echo "🚀 Starting HVAC Scraper..."
docker-compose -f docker-compose.production.yml up -d --build

echo "⏳ Waiting for service to start..."
sleep 30

# Test if service is running
if curl -f http://localhost:$PORT/login > /dev/null 2>&1; then
    echo "✅ Service is running on port $PORT"
else
    echo "❌ Service failed to start. Checking logs..."
    docker-compose -f docker-compose.production.yml logs
    exit 1
fi

echo "🌐 Setting up Nginx..."
# Check if nginx is installed
if ! command -v nginx &> /dev/null; then
    echo "Installing Nginx..."
    apt update
    apt install -y nginx
fi

# Add rate limiting to nginx.conf if not present
if ! grep -q "limit_req_zone" /etc/nginx/nginx.conf; then
    sed -i '/http {/a\\tlimit_req_zone \$binary_remote_addr zone=login:10m rate=5r/m;' /etc/nginx/nginx.conf
fi

# Copy nginx configuration
cp nginx-hvac.conf /etc/nginx/sites-available/hvac-scraper
ln -sf /etc/nginx/sites-available/hvac-scraper /etc/nginx/sites-enabled/

# Test nginx configuration
nginx -t

echo "🔒 Setting up SSL certificate..."
# Install certbot if not present
if ! command -v certbot &> /dev/null; then
    echo "Installing Certbot..."
    apt update
    apt install -y certbot python3-certbot-nginx
fi

# Get SSL certificate
certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN

# Reload nginx
systemctl reload nginx

echo "⏰ Setting up backup cron job..."
# Add backup cron job (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/hvac-scraper/backup.sh") | crontab -

echo "🔧 Setting up log rotation..."
cat > /etc/logrotate.d/hvac-scraper << 'LOGROTATE_EOF'
/opt/hvac-scraper/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
    postrotate
        docker-compose -f /opt/hvac-scraper/docker-compose.production.yml restart hvac-scraper
    endscript
}
LOGROTATE_EOF

echo "🎉 Deployment completed successfully!"
EOF

# Clean up
cd - > /dev/null
rm -rf $TEMP_DIR

echo "✅ Deployment completed!"
echo
echo "🎉 HVAC Scraper Deployment Summary:"
echo "=================================="
echo "✅ Service deployed to your n8n server"
echo "🌐 URL: https://$DOMAIN"
echo "👤 Username: $USERNAME"
echo "🔑 Password: [HIDDEN]"
echo "🔒 SSL: Enabled with Let's Encrypt"
echo "💾 Backups: Daily at 2 AM"
echo "📊 Monitoring: Docker healthcheck enabled"
echo
echo "📋 Server Details:"
echo "   Server: $SERVER_USER@$SERVER_IP"
echo "   Port: $PORT"
echo "   Directory: /opt/hvac-scraper"
echo
echo "🔧 Management Commands (run on server):"
echo "   cd /opt/hvac-scraper"
echo "   ./backup.sh                    # Manual backup"
echo "   ./update.sh                    # Update service"
echo "   docker-compose -f docker-compose.production.yml logs  # View logs"
echo "   docker-compose -f docker-compose.production.yml restart  # Restart"
echo
echo "📱 Share with your sales team:"
echo "   URL: https://$DOMAIN"
echo "   Username: $USERNAME"
echo "   Password: [Provide securely]"
echo
echo "🔐 Security Notes:"
echo "- SSL certificate will auto-renew"
echo "- Login attempts are rate-limited"
echo "- Daily backups are configured"
echo "- Change the password after first team login"
echo
echo "🎯 Your sales team can now access the HVAC scraper securely!"

# Test the deployment
echo "🧪 Testing deployment..."
sleep 5
if curl -f https://$DOMAIN/login > /dev/null 2>&1; then
    echo "✅ Deployment test successful!"
else
    echo "⚠️  Deployment test failed. Please check:"
    echo "   - DNS propagation for $DOMAIN"
    echo "   - SSL certificate installation"
    echo "   - Service status on server"
fi

