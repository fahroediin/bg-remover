# Background Remover API - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Production Deployment Guide](#production-deployment-guide)
3. [Security Considerations](#security-considerations)
4. [Performance Optimization](#performance-optimization)
5. [Monitoring & Logging](#monitoring--logging)
6. [Troubleshooting](#troubleshooting)
7. [API Reference](#api-reference)

## Architecture Overview

### Technology Stack
- **Backend**: Flask (Python Web Framework)
- **Background Removal**: rembg library
- **Image Processing**: PIL (Python Imaging Library)
- **Rate Limiting**: Flask-Limiter
- **CORS**: Flask-CORS
- **Logging**: Python logging module
- **Configuration**: python-dotenv

### System Architecture
```
Client → Load Balancer → Web Server → Flask App → rembg → PIL → File System
                           ↓
                    Redis (Rate Limiting)
                           ↓
                    Log Files (Logging)
```

### Data Flow
1. **Request Processing**: Client sends request to Flask app
2. **Validation**: Input validation and security checks
3. **Rate Limiting**: Check against Redis rate limits
4. **Image Processing**: PIL validation → rembg processing
5. **Response**: Return processed image or error
6. **Logging**: Log all activities and metrics

## Production Deployment Guide

### Prerequisites
- Python 3.8+ or Docker
- Redis server (for rate limiting)
- Web server (Nginx recommended)
- SSL certificate (HTTPS)
- Reverse proxy configuration

### Option 1: Docker Deployment (Recommended)

#### 1. Create Production Dockerfile
```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs logs

# Set environment variables
ENV FLASK_ENV=production
ENV DEBUG=False

# Expose port
EXPOSE 5001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "app:app"]
```

#### 2. Create docker-compose.yml
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - FLASK_ENV=production
      - DEBUG=False
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
```

#### 3. Create Production Environment File
```bash
# .env.production
APP_NAME=Background Remover API
APP_VERSION=1.0.0
DEBUG=False
HOST=0.0.0.0
PORT=5001

# Rate Limiting
RATE_LIMIT_STORAGE=redis
REDIS_URL=redis://redis:6379/0
RATE_LIMIT_REMOVE_BG_PER_HOUR=10
RATE_LIMIT_PREVIEW_PER_HOUR=20
RATE_LIMIT_BASE64_PER_HOUR=30
RATE_LIMIT_READ_FILE_PER_HOUR=15

# Security
CORS_ORIGINS=https://yourdomain.com
MAX_CONTENT_LENGTH=16777216

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/bg_remover.log

# Paths
UPLOAD_DIR=/app/uploads
OUTPUT_DIR=/app/outputs
```

#### 4. Deploy with Docker
```bash
# Build and start services
docker-compose up -d --build

# Check logs
docker-compose logs -f app

# Monitor services
docker-compose ps
```

### Option 2: Manual Deployment

#### 1. Server Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install python3 python3-pip python3-venv nginx redis-server -y

# Create application user
sudo useradd -m -s /bin/bash bgremover
sudo su - bgremover
```

#### 2. Application Setup
```bash
# Clone repository
git clone <repository-url> bg-remover
cd bg-remover

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install gunicorn

# Configure environment
cp .env.sample .env
# Edit .env with production values

# Create directories
mkdir -p uploads outputs logs

# Set permissions
chmod 755 uploads outputs logs
```

#### 3. Gunicorn Service
Create `/etc/systemd/system/bg-remover.service`:
```ini
[Unit]
Description=Background Remover API
After=network.target

[Service]
User=bgremover
Group=bgremover
WorkingDirectory=/home/bgremover/bg-remover
Environment="PATH=/home/bgremover/bg-remover/venv/bin"
ExecStart=/home/bgremover/bg-remover/venv/bin/gunicorn --bind 127.0.0.1:5001 --workers 4 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable bg-remover
sudo systemctl start bg-remover
sudo systemctl status bg-remover
```

#### 4. Nginx Configuration
Create `/etc/nginx/sites-available/bg-remover`:
```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/key.pem;

    # SSL security settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";

    # File upload size limit
    client_max_body_size 16M;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Static file serving (optional)
    location /static/ {
        alias /home/bgremover/bg-remover/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5001/health;
        access_log off;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/bg-remover /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Security Considerations

### 1. Environment Security
```bash
# Secure .env file
chmod 600 .env
chown bgremover:bgremover .env

# Never commit .env to version control
echo ".env" >> .gitignore
```

### 2. File System Security
```bash
# Secure upload directories
chmod 755 uploads outputs
chown bgremover:www-data uploads outputs

# Regular cleanup script
# /etc/cron.hourly/cleanup-bgremover
#!/bin/bash
find /home/bgremover/bg-remover/uploads -type f -mtime +1 -delete
find /home/bgremover/bg-remover/outputs -type f -mtime +1 -delete
```

### 3. Network Security
- Use HTTPS in production
- Configure firewall to allow only necessary ports
- Implement IP whitelisting if needed
- Use Cloudflare or similar DDoS protection

### 4. Application Security
- Set `DEBUG=False` in production
- Use strong secrets for session management
- Implement request validation
- Regular security updates

## Performance Optimization

### 1. Application Level
```python
# Gunicorn configuration
# gunicorn.conf.py
bind = "127.0.0.1:5001"
workers = 4  # Number of CPU cores
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 2
preload_app = True
```

### 2. Redis Optimization
```redis
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. Caching Strategy
- Implement Redis caching for frequent requests
- Use CDN for static assets
- Optimize image compression

### 4. Load Balancing
```nginx
upstream bg_remover {
    server 127.0.0.1:5001;
    server 127.0.0.1:5002;
    server 127.0.0.1:5003;
    server 127.0.0.1:5004;
}

server {
    location / {
        proxy_pass http://bg_remover;
    }
}
```

## Monitoring & Logging

### 1. Application Monitoring
```python
# Add to app.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('bg_remover_requests_total', 'Total requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('bg_remover_request_duration_seconds', 'Request duration')

@app.before_request
def before_request():
    flask.g.start_time = time.time()

@app.after_request
def after_request(response):
    duration = time.time() - flask.g.start_time
    REQUEST_DURATION.observe(duration)
    REQUEST_COUNT.labels(method=request.method, endpoint=request.endpoint).inc()
    return response

@app.route('/metrics')
def metrics():
    if request.remote_addr != '127.0.0.1':
        abort(403)
    return generate_latest()
```

### 2. Log Management
```bash
# Log rotation configuration
# /etc/logrotate.d/bg-remover
/home/bgremover/bg-remover/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 bgremover bgremover
    postrotate
        systemctl reload bg-remover
    endscript
}
```

### 3. Health Checks
```python
@app.route('/health')
def health_check():
    checks = {
        'app': True,
        'redis': check_redis_connection(),
        'disk_space': check_disk_space(),
        'memory': check_memory_usage()
    }

    if all(checks.values()):
        return {'status': 'healthy', 'checks': checks}, 200
    else:
        return {'status': 'unhealthy', 'checks': checks}, 503
```

### 4. Monitoring Setup
```bash
# Install monitoring tools
pip install prometheus-client grafana-api

# Set up Grafana dashboards
# Monitor: CPU, memory, disk space, request rates, error rates
```

## Troubleshooting

### Common Issues

#### 1. High Memory Usage
```bash
# Check memory usage
ps aux | grep gunicorn
top -p $(pgrep -f gunicorn)

# Solutions:
# - Reduce worker count
# - Implement memory limits
# - Optimize image processing
```

#### 2. Redis Connection Issues
```bash
# Check Redis status
redis-cli ping
redis-cli info

# Solutions:
# - Restart Redis service
# - Check network connectivity
# - Verify Redis configuration
```

#### 3. File Upload Issues
```bash
# Check disk space
df -h
du -sh uploads/ outputs/

# Check permissions
ls -la uploads/ outputs/

# Solutions:
# - Clean up old files
# - Increase disk space
# - Fix permissions
```

#### 4. Rate Limiting Problems
```bash
# Check Redis rate limiting data
redis-cli keys "flask_limiter:*"
redis-cli get "flask_limiter:your_key"

# Solutions:
# - Clear Redis cache
# - Adjust rate limits
# - Check Redis storage
```

### Debugging Steps
1. Check application logs
2. Verify system resources
3. Test API endpoints manually
4. Monitor network connections
5. Validate configuration

## API Reference

### Authentication
Currently no authentication required (consider implementing for production).

### Rate Limits
- Applied per IP address
- Stored in Redis
- Configurable per endpoint

### Error Responses
```json
{
  "error": "Error description",
  "solution": "Suggested solution",
  "details": "Additional error details"
}
```

### Success Responses
```json
{
  "success": true,
  "image": "base64_encoded_image",
  "mimetype": "image/png",
  "size": 1024
}
```

### Headers
- `X-RateLimit-Limit`: Rate limit for the endpoint
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Time when limit resets

---

**For additional support, check the application logs and contact the development team.**