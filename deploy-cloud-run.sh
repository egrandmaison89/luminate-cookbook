#!/bin/bash
# Deployment script for Google Cloud Run
# Usage: ./deploy-cloud-run.sh [PROJECT_ID] [REGION]

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get project ID from argument or prompt
PROJECT_ID=${1:-""}
REGION=${2:-"us-central1"}

if [ -z "$PROJECT_ID" ]; then
    echo -e "${YELLOW}Google Cloud Project ID not provided.${NC}"
    echo "Usage: ./deploy-cloud-run.sh [PROJECT_ID] [REGION]"
    echo "Example: ./deploy-cloud-run.sh my-project-id us-central1"
    echo ""
    read -p "Enter your Google Cloud Project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    echo -e "${RED}Error: Project ID is required${NC}"
    exit 1
fi

echo -e "${GREEN}🚀 Deploying Luminate Cookbook to Google Cloud Run${NC}"
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Install it from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Set the project
echo -e "${YELLOW}Setting Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID

# Enable required APIs
echo -e "${YELLOW}Enabling required Google Cloud APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
IMAGE_NAME="gcr.io/$PROJECT_ID/luminate-cookbook"
docker build -t $IMAGE_NAME:latest .

# Push the image to Google Container Registry
echo -e "${YELLOW}Pushing image to Google Container Registry...${NC}"
docker push $IMAGE_NAME:latest

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy luminate-cookbook \
    --image $IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --port 8501 \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "PLAYWRIGHT_BROWSERS_PATH=/ms-playwright" \
    --set-env-vars "STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200"

# Get the service URL
SERVICE_URL=$(gcloud run services describe luminate-cookbook \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)')

echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${GREEN}Your app is available at:${NC}"
echo -e "${GREEN}$SERVICE_URL${NC}"
echo ""
echo "To view logs:"
echo "  gcloud run services logs read luminate-cookbook --region $REGION"
echo ""
echo "To update the deployment:"
echo "  ./deploy-cloud-run.sh $PROJECT_ID $REGION"
