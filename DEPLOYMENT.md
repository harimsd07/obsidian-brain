# Obsidian Brain - Deployment Guide

Complete guide for deploying Obsidian Brain in production environments using Docker, systemd, or cloud platforms.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Docker Deployment](#docker-deployment)
3. [Systemd Service](#systemd-service)
4. [Cloud Deployment](#cloud-deployment)
5. [Production Configuration](#production-configuration)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Local Development
```bash
# Clone and setup
git clone https://github.com/harimsd07/obsidian-brain.git
cd obsidian-brain

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure (interactive setup)
brain init

# Start server
brain serve --host 0.0.0.0 --port 8009
```

Access at: `http://localhost:8009`

---

## Docker Deployment

### Option 1: Docker Compose (Recommended)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  obsidian-brain:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: obsidian-brain
    ports:
      - "8009:8009"
    environment:
      - OLLAMA_API_URL=http://ollama:11434
      - GROQ_API_KEY=${GROQ_API_KEY}
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - NVIDIA_NIM_API_KEY=${NVIDIA_NIM_API_KEY}
      - VAULT_PATH=/data/vault
      - LOG_LEVEL=INFO
    volumes:
      - ./data/vault:/data/vault:ro
      - ./data/chroma:/data/chroma
      - ./data/cache:/data/cache
    depends_on:
      - ollama
    restart: unless-stopped
    networks:
      - brain-network

  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
    volumes:
      - ollama-data:/root/.ollama
    restart: unless-stopped
    networks:
      - brain-network

volumes:
  ollama-data:

networks:
  brain-network:
    driver: bridge
```

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml requirements.txt* ./
COPY brain/ ./brain/
COPY brain/static/ ./brain/static/

# Install Python dependencies
RUN pip install --no-cache-dir -e .

# Create data directories
RUN mkdir -p /data/vault /data/chroma /data/cache

# Expose port
EXPOSE 8009

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8009/health || exit 1

# Run application
CMD ["brain", "serve", "--host", "0.0.0.0", "--port", "8009"]
```

Deploy:

```bash
# Create .env file with API keys
cat > .env << EOF
GROQ_API_KEY=your-groq-key
GEMINI_API_KEY=your-gemini-key
NVIDIA_NIM_API_KEY=your-nvidia-key
EOF

# Start services
docker-compose up -d

# View logs
docker-compose logs -f obsidian-brain

# Stop services
docker-compose down
```

### Option 2: Single Docker Image

```bash
# Build image
docker build -t obsidian-brain:latest .

# Run container
docker run -d \
  --name obsidian-brain \
  -p 8009:8009 \
  -v $(pwd)/data/vault:/data/vault:ro \
  -v $(pwd)/data/chroma:/data/chroma \
  -e GROQ_API_KEY=$GROQ_API_KEY \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  obsidian-brain:latest

# View logs
docker logs -f obsidian-brain

# Stop container
docker stop obsidian-brain
docker rm obsidian-brain
```

---

## Systemd Service

### Setup as Linux Service

Create `/etc/systemd/system/obsidian-brain.service`:

```ini
[Unit]
Description=Obsidian Brain - Chat with your vault
After=network.target
Documentation=https://github.com/harimsd07/obsidian-brain

[Service]
Type=simple
User=obsidian-brain
Group=obsidian-brain
WorkingDirectory=/opt/obsidian-brain

# Python environment
Environment="PATH=/opt/obsidian-brain/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
Environment="VIRTUAL_ENV=/opt/obsidian-brain/.venv"

# API Keys (load from /etc/obsidian-brain/.env)
EnvironmentFile=/etc/obsidian-brain/.env

# Application settings
Environment="LOG_LEVEL=INFO"
Environment="PORT=8009"
Environment="HOST=0.0.0.0"

# Start command
ExecStart=/opt/obsidian-brain/.venv/bin/brain serve --host 0.0.0.0 --port 8009

# Restart policy
Restart=on-failure
RestartSec=10s
StartLimitInterval=1min
StartLimitBurst=5

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/data/chroma /data/cache

[Install]
WantedBy=multi-user.target
```

Installation steps:

```bash
# 1. Create system user
sudo useradd -r -s /bin/bash obsidian-brain

# 2. Create directory structure
sudo mkdir -p /opt/obsidian-brain
sudo mkdir -p /etc/obsidian-brain
sudo mkdir -p /data/{vault,chroma,cache}

# 3. Install application
cd /opt/obsidian-brain
sudo git clone https://github.com/harimsd07/obsidian-brain.git .
sudo python3.11 -m venv .venv
sudo .venv/bin/pip install -e .

# 4. Configure environment
sudo tee /etc/obsidian-brain/.env > /dev/null << EOF
GROQ_API_KEY=your-key
GEMINI_API_KEY=your-key
NVIDIA_NIM_API_KEY=your-key
EOF

# 5. Set permissions
sudo chown -R obsidian-brain:obsidian-brain /opt/obsidian-brain
sudo chown -R obsidian-brain:obsidian-brain /data
sudo chown -R obsidian-brain:obsidian-brain /etc/obsidian-brain

# 6. Enable service
sudo systemctl daemon-reload
sudo systemctl enable obsidian-brain
sudo systemctl start obsidian-brain

# 7. Check status
sudo systemctl status obsidian-brain
sudo journalctl -u obsidian-brain -f
```

---

## Cloud Deployment

### AWS EC2

```bash
#!/bin/bash
# Deploy script for AWS EC2

# Update system
sudo apt-get update && apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev

# Clone repository
cd /opt
sudo git clone https://github.com/harimsd07/obsidian-brain.git
cd obsidian-brain

# Setup virtual environment
sudo python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Configure AWS Systems Manager Parameter Store for secrets
aws ssm put-parameter --name "/obsidian-brain/groq-key" --value "your-key" --type "SecureString"
aws ssm put-parameter --name "/obsidian-brain/gemini-key" --value "your-key" --type "SecureString"

# Run as background service
nohup brain serve --host 0.0.0.0 --port 8009 > /var/log/obsidian-brain.log 2>&1 &
```

### Heroku

Create `Procfile`:

```
web: brain serve --host 0.0.0.0 --port $PORT
```

Deploy:

```bash
# Login to Heroku
heroku login

# Create app
heroku create obsidian-brain

# Set environment variables
heroku config:set GROQ_API_KEY=your-key
heroku config:set GEMINI_API_KEY=your-key
heroku config:set NVIDIA_NIM_API_KEY=your-key

# Deploy
git push heroku main

# View logs
heroku logs -t
```

### Railway

```yaml
# railway.json
{
  "builder": "nixpacks",
  "nixpacks": {
    "providers": ["python"]
  }
}
```

Deploy via Railway dashboard (GitHub integration).

### DigitalOcean App Platform

```yaml
# app.yaml
name: obsidian-brain
services:
  - name: web
    github:
      repo: harimsd07/obsidian-brain
      branch: main
    build_command: pip install -e .
    run_command: brain serve --host 0.0.0.0 --port 8080
    http_port: 8080
    env:
      - key: GROQ_API_KEY
        scope: RUN_AND_BUILD_TIME
      - key: GEMINI_API_KEY
        scope: RUN_AND_BUILD_TIME
```

---

## Production Configuration

### Environment Variables

```bash
# API Keys (required)
GROQ_API_KEY=sk-...
GEMINI_API_KEY=AIzaSy...
NVIDIA_NIM_API_KEY=nvapi-...

# Optional: Ollama
OLLAMA_API_URL=http://localhost:11434

# Application settings
VAULT_PATH=/data/vault
LOG_LEVEL=INFO
PORT=8009
HOST=0.0.0.0

# Performance tuning
MAX_WORKERS=4
BATCH_SIZE=32
CACHE_TTL=3600
RATE_LIMIT_ENABLED=true

# Security
CORS_ORIGINS=https://yourdomain.com
API_KEY_REQUIRED=false
ENABLE_AUTH=false
```

### Nginx Reverse Proxy

```nginx
upstream obsidian_brain {
    server localhost:8009;
}

server {
    listen 80;
    server_name brain.example.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name brain.example.com;
    
    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/brain.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/brain.example.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    
    # Proxy settings
    location / {
        proxy_pass http://obsidian_brain;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;
    limit_req zone=general burst=20;
}
```

### Database Backup

```bash
#!/bin/bash
# Backup ChromaDB and cache

BACKUP_DIR="/backups/obsidian-brain"
DATE=$(date +%Y-%m-%d_%H-%M-%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup ChromaDB
tar -czf $BACKUP_DIR/chroma-$DATE.tar.gz /data/chroma/

# Backup cache
tar -czf $BACKUP_DIR/cache-$DATE.tar.gz /data/cache/

# Keep only last 30 days
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/obsidian-brain/scripts/backup.sh
```

---

## Monitoring & Maintenance

### Health Check Endpoint

```bash
# Check if service is healthy
curl http://localhost:8009/health

# Expected response:
# {"status": "healthy", "uptime_seconds": 3600, ...}
```

### Prometheus Metrics

```bash
# Metrics available at:
curl http://localhost:8009/metrics
```

### Log Monitoring

```bash
# Real-time logs
tail -f /var/log/obsidian-brain.log

# Search logs
grep "ERROR" /var/log/obsidian-brain.log

# View stats page for request counts
curl http://localhost:8009/api/stats
```

### Update Procedure

```bash
# Pull latest changes
cd /opt/obsidian-brain
git pull origin main

# Install any new dependencies
source .venv/bin/activate
pip install -e .

# Run tests
pytest tests/

# Restart service
sudo systemctl restart obsidian-brain

# Verify
curl http://localhost:8009/health
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Find process using port 8009
lsof -i :8009

# Kill process
kill -9 <PID>

# Or use different port
brain serve --host 0.0.0.0 --port 8010
```

#### 2. ChromaDB Connection Error
```bash
# Clear ChromaDB cache (WARNING: will reset embeddings)
rm -rf /data/chroma/*

# Reinitialize
brain init

# Rebuild embeddings
brain index
```

#### 3. Out of Memory
```bash
# Monitor memory usage
watch -n 1 'free -h'

# Reduce batch size in config
# Or increase available RAM
```

#### 4. API Rate Limits
```bash
# Check current limits
curl http://localhost:8009/api/stats

# Limits reset every hour
# Reduce request frequency or upgrade API keys
```

#### 5. SSL/TLS Errors
```bash
# Verify certificates
openssl x509 -in /etc/letsencrypt/live/brain.example.com/fullchain.pem -text -noout

# Renew with Let's Encrypt
certbot renew

# Verify Nginx configuration
sudo nginx -t
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
brain serve --host 0.0.0.0 --port 8009

# Or set in .env
LOG_LEVEL=DEBUG
```

### Performance Tuning

```bash
# Increase worker processes
brain serve --workers 4

# Increase timeout
brain serve --timeout 300

# Monitor performance
curl http://localhost:8009/metrics
```

---

## Security Checklist

- [ ] Use HTTPS in production (SSL/TLS certificates)
- [ ] Enable rate limiting (slowapi)
- [ ] Restrict API key access (environment variables, not git)
- [ ] Use systemd service with reduced privileges
- [ ] Enable firewall rules (allow only needed ports)
- [ ] Set up monitoring and alerts
- [ ] Regular database backups
- [ ] Keep dependencies updated
- [ ] Use strong API keys (20+ characters)
- [ ] Enable CORS restrictions

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/harimsd07/obsidian-brain/issues
- Documentation: https://github.com/harimsd07/obsidian-brain/blob/main/README.md

---

## License

MIT License - See LICENSE file for details
