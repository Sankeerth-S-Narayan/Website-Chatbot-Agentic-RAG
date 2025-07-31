#!/bin/bash

# Stanford Medical Facilities Agent - Google Cloud Deployment Script
# This script deploys the application to Google Cloud Run

set -e

# Configuration
PROJECT_ID="stanford-medical-agent-2024"
REGION="us-central1"
SERVICE_NAME="stanford-medical-agent"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🏥 Stanford Medical Facilities Agent - Google Cloud Deployment${NC}"
echo "=================================================="

# Check if required environment variables are set
check_env_vars() {
    local required_vars=(
        "SUPABASE_URL"
        "SUPABASE_SERVICE_KEY"
        "ANTHROPIC_API_KEY"
        "GROQ_API_KEY"
        "GOOGLE_GENERATIVE_AI_API_KEY"
    )
    
    local missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        for var in "${missing_vars[@]}"; do
            echo "  - $var"
        done
        echo ""
        echo "Please set these variables in your environment or .env file"
        exit 1
    fi
    
    echo -e "${GREEN}✅ All required environment variables are set${NC}"
}

# Build and push Docker image
build_and_push() {
    echo -e "${YELLOW}🔨 Building Docker image...${NC}"
    docker build -t $IMAGE_NAME .
    
    echo -e "${YELLOW}📤 Pushing image to Google Container Registry...${NC}"
    docker push $IMAGE_NAME
    echo -e "${GREEN}✅ Image pushed successfully${NC}"
}

# Deploy to Cloud Run
deploy_to_cloud_run() {
    echo -e "${YELLOW}🚀 Deploying to Google Cloud Run...${NC}"
    
    gcloud run deploy $SERVICE_NAME \
        --image $IMAGE_NAME \
        --platform managed \
        --region $REGION \
        --allow-unauthenticated \
        --port 8501 \
        --memory 2Gi \
        --cpu 2 \
        --max-instances 10 \
        --timeout 300 \
        --set-env-vars "SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,GROQ_API_KEY=$GROQ_API_KEY,GOOGLE_GENERATIVE_AI_API_KEY=$GOOGLE_GENERATIVE_AI_API_KEY" \
        --project $PROJECT_ID
    
    echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
}

# Get service URL
get_service_url() {
    local url=$(gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID --format="value(status.url)")
    echo -e "${GREEN}🌐 Your application is available at:${NC}"
    echo -e "${YELLOW}$url${NC}"
}

# Main execution
main() {
    # Check if gcloud is authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        echo -e "${RED}❌ Not authenticated with Google Cloud. Please run:${NC}"
        echo "gcloud auth login"
        exit 1
    fi
    
    # Check if project is set
    if [ "$PROJECT_ID" = "your-google-cloud-project-id" ]; then
        echo -e "${RED}❌ Please update PROJECT_ID in this script${NC}"
        exit 1
    fi
    
    # Set the project
    gcloud config set project $PROJECT_ID
    
    check_env_vars
    build_and_push
    deploy_to_cloud_run
    get_service_url
    
    echo -e "${GREEN}🎉 Deployment completed! Your Stanford Medical Facilities Agent is now live on Google Cloud Run.${NC}"
}

# Run main function
main "$@" 