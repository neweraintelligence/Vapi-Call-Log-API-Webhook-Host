#!/bin/bash

# Central Call-Log Deployment Script
# Deploys the Vapi webhook service to Google Cloud Functions

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
FUNCTION_NAME="vapi-call-log"
RUNTIME="python39"
REGION="us-central1"
MEMORY="256MB"
TIMEOUT="60s"

echo -e "${GREEN}🚀 Starting deployment of Central Call-Log system...${NC}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed. Please install it first.${NC}"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1 > /dev/null; then
    echo -e "${YELLOW}Please authenticate with Google Cloud:${NC}"
    gcloud auth login
fi

# Prompt for required environment variables if not set
if [ -z "$GOOGLE_SHEET_ID" ]; then
    echo -e "${YELLOW}Enter your Google Sheet ID:${NC}"
    read -r GOOGLE_SHEET_ID
fi

if [ -z "$VAPI_WEBHOOK_SECRET" ]; then
    echo -e "${YELLOW}Enter your Vapi webhook secret:${NC}"
    read -r VAPI_WEBHOOK_SECRET
fi

# Optional: Set project if not already set
CURRENT_PROJECT=$(gcloud config get-value project 2>/dev/null)
if [ -z "$CURRENT_PROJECT" ]; then
    echo -e "${YELLOW}Enter your Google Cloud Project ID:${NC}"
    read -r PROJECT_ID
    gcloud config set project "$PROJECT_ID"
fi

echo -e "${GREEN}✓ Configuration validated${NC}"

# Check if credentials.json exists
if [ ! -f "credentials.json" ]; then
    echo -e "${RED}Warning: credentials.json not found. Make sure to set GOOGLE_CREDENTIALS_JSON as environment variable in Cloud Functions.${NC}"
    echo -e "${YELLOW}You can do this in the Cloud Console after deployment.${NC}"
fi

# Run tests before deployment
echo -e "${GREEN}🧪 Running tests...${NC}"
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt > /dev/null 2>&1
fi

if command -v pytest &> /dev/null; then
    pytest tests/ -v
    if [ $? -ne 0 ]; then
        echo -e "${RED}Tests failed. Aborting deployment.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ All tests passed${NC}"
else
    echo -e "${YELLOW}Warning: pytest not found. Skipping tests.${NC}"
fi

# Deploy function
echo -e "${GREEN}🚀 Deploying to Google Cloud Functions...${NC}"

gcloud functions deploy "$FUNCTION_NAME" \
    --runtime="$RUNTIME" \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point=main \
    --memory="$MEMORY" \
    --timeout="$TIMEOUT" \
    --region="$REGION" \
    --set-env-vars="GOOGLE_SHEET_ID=$GOOGLE_SHEET_ID,VAPI_WEBHOOK_SECRET=$VAPI_WEBHOOK_SECRET,SHEET_NAME=${SHEET_NAME:-Raw}" \
    --source=. \
    --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Deployment successful!${NC}"
    
    # Get the function URL
    FUNCTION_URL=$(gcloud functions describe "$FUNCTION_NAME" --region="$REGION" --format="value(httpsTrigger.url)")
    
    echo -e "${GREEN}📡 Your webhook endpoint is ready:${NC}"
    echo -e "${YELLOW}$FUNCTION_URL/webhook${NC}"
    echo ""
    echo -e "${GREEN}🔧 Next steps:${NC}"
    echo "1. Configure this URL in your Vapi dashboard"
    echo "2. Set the webhook secret to: $VAPI_WEBHOOK_SECRET"
    echo "3. Test with: curl -X GET $FUNCTION_URL/health"
    echo ""
    echo -e "${GREEN}📊 Monitor your function:${NC}"
    echo "https://console.cloud.google.com/functions/details/$REGION/$FUNCTION_NAME"
    
else
    echo -e "${RED}❌ Deployment failed. Check the error messages above.${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment complete!${NC}" 