# Deployment Guide

This guide covers deploying the Mid-term Stock Planner dashboard online.

## Deployment Options

### Option 1: Streamlit Cloud (Recommended - Free & Easy)

Streamlit Cloud is the easiest way to deploy Streamlit apps. It's free for public repositories.

#### Prerequisites
1. GitHub account
2. Repository pushed to GitHub (public or private with Streamlit Cloud access)

#### Steps

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Prepare for deployment"
   git push origin main
   ```

2. **Sign up for Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Sign in with your GitHub account

3. **Deploy your app**
   - Click "New app"
   - Select your repository: `antiwong/midterm-stock-planner`
   - Main file path: `src/app/dashboard/app.py`
   - App URL: Choose a custom subdomain (e.g., `midterm-stock-planner`)
   - Click "Deploy"

4. **Configure Environment Variables**
   In the Streamlit Cloud dashboard, add these secrets:
   - `GEMINI_API_KEY`: Your Google Gemini API key (for AI insights)
   - `ALPHA_VANTAGE_API_KEY`: (Optional) For additional data sources

5. **Access your app**
   - Your app will be available at: `https://midterm-stock-planner.streamlit.app`
   - Updates are automatically deployed when you push to GitHub

#### Streamlit Cloud Configuration

The app is configured via `.streamlit/config.toml`. Key settings:
- Server runs in headless mode
- Port 8501
- CORS disabled (for security)

### Option 2: Docker Deployment

For more control, you can containerize the app.

#### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# Run Streamlit
CMD ["streamlit", "run", "src/app/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

#### Build and Run

```bash
# Build image
docker build -t midterm-stock-planner .

# Run container
docker run -p 8501:8501 \
  -e GEMINI_API_KEY=your_key_here \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/output:/app/output \
  midterm-stock-planner
```

#### Deploy to Cloud Platforms

**AWS (ECS/Fargate):**
- Push Docker image to ECR
- Create ECS task definition
- Deploy to Fargate with load balancer

**Google Cloud Run:**
```bash
gcloud run deploy midterm-stock-planner \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

**Azure Container Instances:**
- Push to Azure Container Registry
- Deploy via Azure Portal or CLI

**Heroku:**
```bash
# Create Procfile
echo "web: streamlit run src/app/dashboard/app.py --server.port=\$PORT --server.address=0.0.0.0" > Procfile

# Deploy
heroku create midterm-stock-planner
heroku config:set GEMINI_API_KEY=your_key_here
git push heroku main
```

### Option 3: VPS/Server Deployment

For a dedicated server or VPS:

1. **Install dependencies**
   ```bash
   sudo apt update
   sudo apt install python3-pip python3-venv nginx
   ```

2. **Set up application**
   ```bash
   git clone https://github.com/antiwong/midterm-stock-planner.git
   cd midterm-stock-planner
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run with systemd service**
   Create `/etc/systemd/system/stock-planner.service`:
   ```ini
   [Unit]
   Description=Mid-term Stock Planner Dashboard
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/path/to/midterm-stock-planner
   Environment="PATH=/path/to/midterm-stock-planner/venv/bin"
   Environment="GEMINI_API_KEY=your_key_here"
   ExecStart=/path/to/midterm-stock-planner/venv/bin/streamlit run src/app/dashboard/app.py --server.port=8501 --server.address=0.0.0.0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Configure Nginx reverse proxy**
   Create `/etc/nginx/sites-available/stock-planner`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_read_timeout 86400;
       }
   }
   ```

5. **Enable and start**
   ```bash
   sudo systemctl enable stock-planner
   sudo systemctl start stock-planner
   sudo ln -s /etc/nginx/sites-available/stock-planner /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Environment Variables

Set these environment variables for full functionality:

- `GEMINI_API_KEY`: Required for AI insights and commentary
- `ALPHA_VANTAGE_API_KEY`: Optional, for additional data sources
- `DATABASE_URL`: Optional, for custom database connection

## Data Persistence

The app stores data in:
- `data/`: Price data, fundamentals, database
- `output/`: Analysis results, reports
- `models/`: Trained ML models

For production deployments, consider:
1. **Persistent volumes** for data storage
2. **Database backups** (SQLite → PostgreSQL migration for production)
3. **Model versioning** and storage

## Security Considerations

1. **API Keys**: Never commit API keys to Git. Use environment variables or secrets management.
2. **Authentication**: Streamlit Cloud supports password protection. For other deployments, add authentication middleware.
3. **Rate Limiting**: Implement rate limiting for API calls to prevent abuse.
4. **HTTPS**: Always use HTTPS in production (Let's Encrypt for free certificates).

## Monitoring

- **Streamlit Cloud**: Built-in analytics and error tracking
- **Custom deployments**: Use tools like:
  - Sentry for error tracking
  - Prometheus + Grafana for metrics
  - Log aggregation (ELK stack, CloudWatch, etc.)

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are in `requirements.txt`
2. **Port conflicts**: Change port in `.streamlit/config.toml` or deployment config
3. **File permissions**: Ensure app has read/write access to `data/` and `output/` directories
4. **Memory issues**: Increase memory limits for large datasets

### Debug Mode

For local debugging:
```bash
streamlit run src/app/dashboard/app.py --logger.level=debug
```

## Cost Estimates

- **Streamlit Cloud**: Free for public repos, $20/month for private repos
- **AWS/GCP/Azure**: Pay-as-you-go, typically $5-50/month for small deployments
- **VPS**: $5-20/month (DigitalOcean, Linode, etc.)

## Next Steps

1. Choose a deployment option
2. Set up environment variables
3. Test deployment locally first
4. Deploy to production
5. Set up monitoring and backups

For questions or issues, refer to the main [README.md](README.md) or open an issue on GitHub.
