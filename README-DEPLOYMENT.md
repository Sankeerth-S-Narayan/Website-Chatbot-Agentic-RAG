# Stanford Medical Facilities Agent - Deployment Guide

This guide will help you containerize and deploy the Stanford Medical Facilities Agent to Google Cloud Run.

## 🏗️ Architecture Overview

The application consists of:
- **Streamlit UI** - Web interface for user interactions
- **RAG Expert** - AI-powered question answering system
- **Supabase Database** - Vector storage for embeddings
- **Sentence Transformers** - Embedding generation

## 📋 Prerequisites

### 1. Google Cloud Setup
```bash
# Install Google Cloud CLI
# Download from: https://cloud.google.com/sdk/docs/install

# Authenticate with Google Cloud
gcloud auth login

# Set your project ID
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
```

### 2. Docker Setup
```bash
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
```

### 3. Environment Variables
Create a `.env` file based on `env.example`:
```bash
cp env.example .env
# Edit .env with your actual API keys and configuration
```

## 🐳 Local Testing with Docker

### 1. Build and Run Locally
```bash
# Build the Docker image
docker build -t stanford-medical-agent .

# Run with docker-compose (recommended)
docker-compose up --build

# Or run directly with Docker
docker run -p 8501:8501 --env-file .env stanford-medical-agent
```

### 2. Test the Application
- Open your browser to `http://localhost:8501`
- Verify the application loads correctly
- Test a sample query about Stanford medical facilities

## ☁️ Google Cloud Deployment

### Option 1: Automated Deployment (Recommended)

#### 1. Update Configuration
Edit `deploy.sh` and set your project ID:
```bash
PROJECT_ID="your-actual-project-id"
```

#### 2. Set Environment Variables
```bash
export SUPABASE_URL="your-supabase-url"
export SUPABASE_SERVICE_KEY="your-supabase-service-key"
export ANTHROPIC_API_KEY="your-anthropic-api-key"
export GROQ_API_KEY="your-groq-api-key"
export GOOGLE_GENERATIVE_AI_API_KEY="your-google-api-key"
```

#### 3. Run Deployment
```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option 2: Manual Deployment

#### 1. Build and Push Image
```bash
# Build image
docker build -t gcr.io/YOUR_PROJECT_ID/stanford-medical-agent .

# Push to Google Container Registry
docker push gcr.io/YOUR_PROJECT_ID/stanford-medical-agent
```

#### 2. Deploy to Cloud Run
```bash
gcloud run deploy stanford-medical-agent \
  --image gcr.io/YOUR_PROJECT_ID/stanford-medical-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY,GROQ_API_KEY=$GROQ_API_KEY,GOOGLE_GENERATIVE_AI_API_KEY=$GOOGLE_GENERATIVE_AI_API_KEY"
```

### Option 3: Cloud Build (CI/CD)

#### 1. Update cloudbuild.yaml
Edit the substitutions section with your actual values:
```yaml
substitutions:
  _SUPABASE_URL: 'your-actual-supabase-url'
  _SUPABASE_SERVICE_KEY: 'your-actual-supabase-service-key'
  # ... other variables
```

#### 2. Trigger Build
```bash
gcloud builds submit --config cloudbuild.yaml
```

## 🔧 Configuration Options

### Resource Allocation
The application is configured with:
- **Memory**: 2GB (sufficient for embedding model)
- **CPU**: 2 cores
- **Max Instances**: 10 (auto-scaling)
- **Timeout**: 300 seconds (5 minutes)

### Environment Variables
| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service role key | ✅ |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | ✅ |
| `GROQ_API_KEY` | Groq API key | ✅ |
| `GOOGLE_GENERATIVE_AI_API_KEY` | Google Generative AI API key | ✅ |

## 🚀 Post-Deployment

### 1. Verify Deployment
```bash
# Get service URL
gcloud run services describe stanford-medical-agent \
  --region=us-central1 \
  --format="value(status.url)"
```

### 2. Monitor Logs
```bash
# View real-time logs
gcloud run services logs tail stanford-medical-agent --region=us-central1
```

### 3. Scale if Needed
```bash
# Update resources
gcloud run services update stanford-medical-agent \
  --region=us-central1 \
  --memory=4Gi \
  --cpu=4
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check Docker build logs
docker build -t test-image . 2>&1 | tee build.log

# Common solutions:
# - Ensure all files are present
# - Check .dockerignore exclusions
# - Verify requirements.txt format
```

#### 2. Runtime Errors
```bash
# Check container logs
docker logs <container_id>

# Common issues:
# - Missing environment variables
# - Database connection issues
# - API key authentication failures
```

#### 3. Performance Issues
- Increase memory allocation (4Gi recommended for production)
- Add CPU cores for better parallel processing
- Consider using Cloud Run with CPU always allocated

### Health Checks
The application includes health checks:
- **Endpoint**: `/_stcore/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3

## 📊 Monitoring and Scaling

### Cloud Run Metrics
Monitor these key metrics:
- **Request count** - Traffic volume
- **Request latency** - Response times
- **Memory utilization** - Resource usage
- **CPU utilization** - Processing load

### Auto-scaling
The service automatically scales:
- **Min instances**: 0 (cost optimization)
- **Max instances**: 10 (performance limit)
- **Scaling**: Based on request volume

## 🔐 Security Considerations

### 1. Environment Variables
- Store sensitive data in Google Secret Manager
- Use Cloud Run's built-in secret management
- Never commit API keys to version control

### 2. Network Security
- Use VPC connectors for private networking
- Implement proper IAM roles
- Enable Cloud Audit Logging

### 3. Container Security
- Run as non-root user (configured in Dockerfile)
- Regular security updates
- Vulnerability scanning

## 💰 Cost Optimization

### 1. Resource Tuning
- Start with 2GB memory, scale as needed
- Use CPU auto-scaling
- Set appropriate max instances

### 2. Traffic Management
- Implement caching strategies
- Use CDN for static assets
- Optimize embedding model loading

## 🎯 Next Steps

1. **Set up monitoring** with Cloud Monitoring
2. **Configure alerts** for critical metrics
3. **Implement CI/CD** with Cloud Build
4. **Add custom domain** with Cloud Load Balancing
5. **Set up backup strategies** for your database

---

**Need Help?** Check the main README.md for application-specific documentation or create an issue for deployment-related questions. 