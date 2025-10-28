# Background Remover API - Deployment Guide

## Overview
Background Remover API dengan rate limiting dan konfigurasi environment variables yang aman untuk production deployment.

## Features
- ✅ Rate limiting per endpoint
- ✅ Environment-based configuration
- ✅ File upload validation
- ✅ CORS protection
- ✅ Error handling
- ✅ Auto-cleanup old files
- ✅ Multiple output formats (file download, preview, base64)

## Quick Start

### 1. Development
```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python app.py
```

### 2. Production Deployment

#### A. Using Environment File
```bash
# Copy production config
cp .env.production .env

# Install dependencies
pip install -r requirements.txt

# Start production server
python app.py
```

#### B. Using Environment Variables
```bash
# Set environment variables
export FLASK_ENV=production
export DEBUG=False
export RATE_LIMIT_REMOVE_BG_PER_MINUTE=5
export RATE_LIMIT_STORAGE=redis
export REDIS_URL=redis://localhost:6379/0

# Start server
python app.py
```

## Rate Limiting Configuration

### Development Limits (.env)
- **Default**: 1000/hour, 100/minute
- **Background Removal**: 10/minute
- **Preview**: 15/minute
- **Base64**: 12/minute
- **Health**: 200/minute
- **Info**: 60/minute

### Production Limits (.env.production)
- **Default**: 500/hour, 50/minute
- **Background Removal**: 5/minute ⚡ **Stricter**
- **Preview**: 8/minute
- **Base64**: 6/minute
- **Health**: 100/minute
- **Info**: 30/minute

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | True | Enable/disable debug mode |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 5001 | Server port |
| `RATE_LIMIT_STORAGE` | memory | Storage backend (memory/redis) |
| `REDIS_URL` | - | Redis connection URL |
| `MAX_CONTENT_LENGTH` | 16777216 | Max file size (16MB) |
| `CORS_ORIGINS` | * | Allowed CORS origins |

## API Endpoints

### Background Removal
- `POST /remove-background` - Download file hasil
- `POST /remove-background-preview` - Preview di browser
- `POST /remove-background-base64` - Base64 input/output

### System
- `GET /` - API info dan rate limits
- `GET /health` - Health check

## Rate Limiting Headers
Ketika rate limit ter-exceed:
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. 10 per minute",
  "retry_after": "45"
}
```

## Deployment Options

### 1. Direct Python
```bash
python app.py
```

### 2. Gunicorn (Recommended)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5001 app:app
```

### 3. Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

### 4. Docker Compose dengan Redis
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "5001:5001"
    environment:
      - RATE_LIMIT_STORAGE=redis
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
```

## Security Recommendations

### 1. Environment Variables
- Jangan pernah commit `.env` ke version control
- Gunakan `.env.production` untuk template production
- Set sensitive variables di production environment

### 2. CORS
```bash
# Limit CORS origins di production
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### 3. Rate Limiting
- Gunakan Redis storage untuk production
- Set limits yang sesuai dengan kapasitas server
- Monitor rate limit violations

### 4. File Upload
- Max file size: 16MB (configurable)
- Valid extensions: png, jpg, jpeg, gif, bmp, tiff, webp
- Auto-cleanup files setiap 1 jam

## Monitoring

### Health Check
```bash
curl http://localhost:5001/health
```

### Rate Limit Status
```bash
curl http://localhost:5001/ | jq '.rate_limits'
```

## Testing

### Test Rate Limiting
```bash
# Test 15 requests ke endpoint (limit 10/minute)
for i in {1..15}; do
  curl -X POST -F "file=@test.jpg" http://localhost:5001/remove-background-preview
  echo "Request $i"
done
```

### Test Load
```bash
# Install Apache Bench
ab -n 100 -c 10 http://localhost:5001/health
```

## Troubleshooting

### Common Issues

1. **Rate Limit Not Working**
   - Pastikan Flask-Limiter terinstall
   - Check environment variables
   - Restart server setelah ubah .env

2. **Redis Connection Error**
   - Pastikan Redis berjalan: `redis-server`
   - Check Redis URL: `redis://localhost:6379/0`

3. **File Upload Too Large**
   - Adjust `MAX_CONTENT_LENGTH` di .env
   - Check client-side upload limits

4. **CORS Issues**
   - Set `CORS_ORIGINS` ke domain yang benar
   - Check preflight OPTIONS requests

### Debug Mode
```bash
# Enable debug mode untuk detail error
DEBUG=True python app.py
```

## Production Checklist

- [ ] Copy `.env.production` ke `.env`
- [ ] Set `DEBUG=False`
- [ ] Configure Redis storage
- [ ] Set appropriate rate limits
- [ ] Configure CORS origins
- [ ] Set up monitoring
- [ ] Test rate limiting
- [ ] Test file upload limits
- [ ] Set up log rotation
- [ ] Configure backup strategy

## Support

Untuk issues atau questions:
1. Check health endpoint: `GET /health`
2. Review rate limits: `GET /`
3. Check server logs
4. Verify environment variables