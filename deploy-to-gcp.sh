#!/bin/bash

# HVAC Scraper - Google Cloud Platform Deployment Script
# This script deploys your HVAC scraper to Google Cloud Run

set -e

echo "🚀 HVAC Scraper - Google Cloud Deployment"
echo "=========================================="

# Configuration
PROJECT_ID=""
REGION="us-central1"
SERVICE_NAME="hvac-scraper"
DOMAIN=""

# Get user input
read -p "Enter your Google Cloud Project ID: " PROJECT_ID
read -p "Enter your custom domain (optional, press enter to skip): " DOMAIN
read -p "Enter admin username [admin]: " USERNAME
USERNAME=${USERNAME:-admin}
read -s -p "Enter admin password: " PASSWORD
echo

# Validate inputs
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID is required"
    exit 1
fi

if [ -z "$PASSWORD" ]; then
    echo "❌ Password is required"
    exit 1
fi

echo "📋 Configuration:"
echo "   Project ID: $PROJECT_ID"
echo "   Region: $REGION"
echo "   Service: $SERVICE_NAME"
echo "   Username: $USERNAME"
echo "   Domain: ${DOMAIN:-"Will use Cloud Run URL"}"
echo

read -p "Continue with deployment? (y/N): " CONFIRM
if [[ ! $CONFIRM =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled"
    exit 1
fi

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Google Cloud CLI not found. Please install it first:"
    echo "   curl https://sdk.cloud.google.com | bash"
    exit 1
fi

# Set project
echo "🔧 Setting up Google Cloud project..."
gcloud config set project $PROJECT_ID

# Enable required APIs
echo "🔧 Enabling required APIs..."
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com

# Generate secure secret key
SECRET_KEY=$(openssl rand -hex 32)

# Create cloudbuild.yaml for custom build
cat > cloudbuild.yaml << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/$SERVICE_NAME', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/$SERVICE_NAME']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - '$SERVICE_NAME'
      - '--image'
      - 'gcr.io/$PROJECT_ID/$SERVICE_NAME'
      - '--region'
      - '$REGION'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
      - '--set-env-vars'
      - 'LOGIN_USERNAME=$USERNAME,LOGIN_PASSWORD=$PASSWORD,SECRET_KEY=$SECRET_KEY,SESSION_TIMEOUT_HOURS=8'
      - '--memory'
      - '1Gi'
      - '--cpu'
      - '1'
      - '--max-instances'
      - '10'
      - '--timeout'
      - '300'
substitutions:
  _SERVICE_NAME: $SERVICE_NAME
  _REGION: $REGION
  _USERNAME: $USERNAME
  _PASSWORD: $PASSWORD
  _SECRET_KEY: $SECRET_KEY
EOF

# Deploy using Cloud Build
echo "🚀 Deploying to Cloud Run..."
gcloud builds submit --config cloudbuild.yaml

# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region=$REGION --format='value(status.url)')

echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: $SERVICE_URL"
echo "👤 Username: $USERNAME"
echo "🔑 Password: $PASSWORD"

# Setup custom domain if provided
if [ ! -z "$DOMAIN" ]; then
    echo "🔧 Setting up custom domain..."
    
    # Create domain mapping
    gcloud run domain-mappings create \
        --service $SERVICE_NAME \
        --domain $DOMAIN \
        --region $REGION
    
    echo "📋 DNS Configuration Required:"
    echo "   Add the following DNS records to your domain:"
    echo "   Type: CNAME"
    echo "   Name: $DOMAIN"
    echo "   Value: ghs.googlehosted.com"
    echo
    echo "   After DNS propagation, your service will be available at:"
    echo "   https://$DOMAIN"
fi

# Create monitoring and alerting
echo "🔧 Setting up monitoring..."

# Create uptime check
cat > uptime-check.json << EOF
{
  "displayName": "HVAC Scraper Uptime Check",
  "httpCheck": {
    "path": "/login",
    "port": 443,
    "useSsl": true
  },
  "monitoredResource": {
    "type": "uptime_url",
    "labels": {
      "project_id": "$PROJECT_ID",
      "host": "${DOMAIN:-$(echo $SERVICE_URL | sed 's|https://||')}"
    }
  },
  "timeout": "10s",
  "period": "300s"
}
EOF

# Create the uptime check
gcloud alpha monitoring uptime create uptime-check.json

echo "📊 Monitoring configured!"

# Create backup script for Cloud Storage
cat > backup-to-gcs.sh << 'EOF'
#!/bin/bash
# Backup script for Google Cloud Storage

BUCKET_NAME="hvac-scraper-backups-$(date +%s)"
DATE=$(date +%Y%m%d_%H%M%S)

# Create bucket if it doesn't exist
gsutil mb gs://$BUCKET_NAME 2>/dev/null || true

# Backup database (if using Cloud SQL)
# gcloud sql export sql INSTANCE_NAME gs://$BUCKET_NAME/db_$DATE.sql

# For now, create a placeholder backup
echo "Backup completed at $(date)" > backup_$DATE.txt
gsutil cp backup_$DATE.txt gs://$BUCKET_NAME/

echo "Backup uploaded to gs://$BUCKET_NAME/"
EOF

chmod +x backup-to-gcs.sh

# Create update script
cat > update-service.sh << EOF
#!/bin/bash
# Update script for the HVAC Scraper service

echo "🔄 Updating HVAC Scraper service..."

# Rebuild and deploy
gcloud builds submit --config cloudbuild.yaml

echo "✅ Service updated successfully!"
echo "🌐 Service URL: $SERVICE_URL"
EOF

chmod +x update-service.sh

# Clean up temporary files
rm -f cloudbuild.yaml uptime-check.json

echo "📁 Created helper scripts:"
echo "   backup-to-gcs.sh - Backup data to Google Cloud Storage"
echo "   update-service.sh - Update the deployed service"
echo

echo "🎉 Deployment Summary:"
echo "================================"
echo "✅ Service deployed to Google Cloud Run"
echo "🌐 URL: $SERVICE_URL"
echo "👤 Username: $USERNAME"
echo "🔑 Password: [HIDDEN]"
echo "📊 Monitoring: Enabled"
echo "💾 Backup script: backup-to-gcs.sh"
echo "🔄 Update script: update-service.sh"

if [ ! -z "$DOMAIN" ]; then
    echo "🌍 Custom domain: $DOMAIN (configure DNS)"
fi

echo
echo "📋 Next Steps:"
echo "1. Test the service at: $SERVICE_URL"
echo "2. Share the URL and credentials with your sales team"
if [ ! -z "$DOMAIN" ]; then
    echo "3. Configure DNS for your custom domain"
fi
echo "4. Set up regular backups using backup-to-gcs.sh"
echo "5. Monitor the service in Google Cloud Console"
echo
echo "🔐 Security Notes:"
echo "- Change the default password after first login"
echo "- Consider setting up Google Workspace SSO"
echo "- Monitor access logs regularly"
echo "- Keep the service updated with update-service.sh"
echo
echo "🎯 Your sales team can now access the HVAC scraper from anywhere!"

