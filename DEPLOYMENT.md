# Background Remover API - Deployment Guide

## Overview
Background Remover API dengan rate limiting, advanced image optimization, dan konfigurasi environment variables yang aman untuk production deployment.

## Features
- ✅ Rate limiting per endpoint
- ✅ Environment-based configuration
- ✅ File upload validation
- ✅ CORS protection
- ✅ Error handling
- ✅ Auto-cleanup old files
- ✅ Multiple output formats (file download, preview, base64)
- ✅ **Advanced Image Optimization** (up to 90% size reduction)
- ✅ **Multiple output formats** (JPEG, WEBP, PNG)
- ✅ **Quality and dimension control**
- ✅ **Compression monitoring**

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

## Image Optimization Deployment

### Optimization Features
- **Format Conversion**: JPEG, WEBP, PNG dengan kompresi optimal
- **Quality Control**: 10-100% quality adjustment
- **Dimension Resizing**: Smart scaling dengan aspect ratio preservation
- **Compression Monitoring**: Real-time size reduction tracking
- **Performance Impact**: +200-500ms processing time

### Optimization Configuration
```bash
# Default optimization settings
DEFAULT_FORMAT=JPEG
DEFAULT_QUALITY=80
MAX_WIDTH=4000
MAX_HEIGHT=4000
COMPRESSION_LOGGING=True
```

### Production Optimization Presets
```bash
# Environment-based optimization presets
OPTIMIZATION_PRESET_WEB=JPEG,80,1200,800
OPTIMIZATION_PRESET_SOCIAL=PNG,90,1080,1080
OPTIMIZATION_PRESET_MOBILE=WEBP,70,800,600
OPTIMIZATION_PRESET_THUMBNAIL=WEBP,60,300,300
```

### Resource Requirements
- **Memory**: +20MB per concurrent optimization
- **CPU**: +25% usage during optimization
- **Storage**: Temporary files auto-cleaned after 1 hour
- **Bandwidth**: 70-90% reduction in outbound transfer

## API Endpoints

### Background Removal with Optimization
- `POST /remove-background` - Download file hasil optimized
  - **Optimization Parameters**: format, quality, max_width, max_height
- `POST /remove-background-preview` - Preview optimized di browser
  - **Optimization Parameters**: format, quality, max_width, max_height
- `POST /remove-background-base64` - Base64 input/output optimized
  - **Optimization Parameters**: image, format, quality, max_width, max_height

### System
- `GET /` - API info, rate limits, dan optimization stats
- `GET /health` - Health check dengan optimization status

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

### 3. Docker dengan Optimization Support
```dockerfile
FROM python:3.11-slim

# Install system dependencies for image processing
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories with proper permissions
RUN mkdir -p uploads outputs logs && \
    chmod 755 uploads outputs logs

# Environment variables for optimization
ENV FLASK_ENV=production
ENV DEBUG=False
ENV DEFAULT_FORMAT=JPEG
ENV DEFAULT_QUALITY=80
ENV COMPRESSION_LOGGING=True

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

EXPOSE 5001

# Use gunicorn for production
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "app:app"]
```

### 4. Docker Compose Production dengan Redis dan Optimization
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
      - RATE_LIMIT_STORAGE=redis
      - REDIS_URL=redis://redis:6379/0
      - DEFAULT_FORMAT=JPEG
      - DEFAULT_QUALITY=80
      - MAX_WIDTH=4000
      - MAX_HEIGHT=4000
      - COMPRESSION_LOGGING=True
    depends_on:
      - redis
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5001/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    restart: unless-stopped

volumes:
  redis_data:
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

### Test Image Optimization
```bash
# Test optimization dengan berbagai format
curl -X POST http://localhost:5001/remove-background-base64 \
  -H 'Content-Type: application/json' \
  -d '{
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "format": "JPEG",
    "quality": 80,
    "max_width": 1200,
    "max_height": 800
  }' | jq '.size, .optimization.compression_ratio'

# Test WEBP optimization
curl -X POST http://localhost:5001/remove-background-base64 \
  -H 'Content-Type: application/json' \
  -d '{
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "format": "WEBP",
    "quality": 70
  }'
```

### Test Load dengan Optimization
```bash
# Install Apache Bench
ab -n 100 -c 10 http://localhost:5001/health

# Test load pada endpoint optimization
ab -n 50 -c 5 -p test_image.jpg -F "file=@test_image.jpg;format=JPEG;quality=80" \
  http://localhost:5001/remove-background-preview
```

### Performance Benchmarking
```bash
# Create benchmark script
cat > benchmark_optimization.sh << 'EOF'
#!/bin/bash

echo "=== Image Optimization Benchmark ==="

# Test dengan berbagai ukuran dan format
for format in "JPEG" "WEBP" "PNG"; do
  for quality in 60 80 95; do
    echo "Testing $format at $quality% quality..."

    start_time=$(date +%s%N)

    curl -s -X POST http://localhost:5001/remove-background-base64 \
      -H 'Content-Type: application/json' \
      -d "{\"image\":\"$(base64 -w 0 test_image.jpg)\",\"format\":\"$format\",\"quality\":$quality}" \
      -o "output_${format}_${quality}.jpg"

    end_time=$(date +%s%N)
    duration=$(( (end_time - start_time) / 1000000 ))

    echo "  Duration: ${duration}ms"
    echo "  Output size: $(stat -c%s "output_${format}_${quality}.jpg") bytes"
  done
done

echo "=== Benchmark Complete ==="
EOF

chmod +x benchmark_optimization.sh
./benchmark_optimization.sh
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

5. **Optimization Not Working**
   - Verify PIL library installed correctly
   - Check image format support
   - Review optimization parameters
   - Test dengan different quality/format settings

6. **High Memory Usage During Optimization**
   - Reduce concurrent workers
   - Implement memory limits
   - Monitor optimization queue
   - Consider image size limits

7. **Slow Performance with Large Images**
   - Implement dimension limits
   - Use quality reduction
   - Add processing timeout
   - Consider background processing

8. **Optimization Quality Issues**
   - Adjust quality parameters
   - Test different output formats
   - Verify input image quality
   - Check compression settings

### Debug Mode
```bash
# Enable debug mode untuk detail error
DEBUG=True python app.py
```

## Production Checklist

### Basic Configuration
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

### Optimization Configuration
- [ ] Set default optimization format (JPEG/WEBP/PNG)
- [ ] Configure default quality settings (60-95%)
- [ ] Set maximum dimensions (4000x4000px recommended)
- [ ] Enable compression logging
- [ ] Test optimization with different formats
- [ ] Verify compression ratios (70-90% expected)
- [ ] Monitor memory usage during optimization
- [ ] Test performance with large images
- [ ] Configure optimization timeouts
- [ ] Set up optimization monitoring

### Performance Testing
- [ ] Benchmark image processing speeds
- [ ] Test concurrent optimization requests
- [ ] Validate compression quality vs file size
- [ ] Monitor CPU and memory usage
- [ ] Test with various image formats and sizes
- [ ] Verify rate limiting with optimization enabled
- [ ] Load test with optimization parameters

### Security & Monitoring
- [ ] Validate optimization parameters
- [ ] Monitor file size reductions
- [ ] Track optimization performance metrics
- [ ] Set up alerts for high memory usage
- [ ] Monitor optimization success/failure rates
- [ ] Log optimization metrics for analysis

## Support

Untuk issues atau questions:
1. Check health endpoint: `GET /health`
2. Review rate limits: `GET /`
3. Check server logs
4. Verify environment variables
5. **Monitor optimization metrics** di log files
6. **Test optimization parameters** dengan different settings
7. **Review compression ratios** dan performance metrics

## Performance Metrics & Monitoring

### Key Optimization Metrics
Monitor these metrics untuk optimal performance:

```bash
# Monitor optimization performance
tail -f logs/bg_remover.log | grep "optimized"

# Check compression ratios
grep "Image optimized" logs/bg_remover.log | tail -20

# Monitor processing times
grep "Processing" logs/bg_remover.log | tail -20
```

### Expected Performance Benchmarks
- **Processing Time**: 200-500ms per image (with optimization)
- **Memory Usage**: +20MB during optimization
- **CPU Impact**: +25% during processing
- **Compression Ratio**: 70-90% size reduction
- **Success Rate**: >95% for valid images

### Monitoring Commands
```bash
# System resource monitoring
htop
iotop
df -h

# Application-specific monitoring
curl -s http://localhost:5001/health | jq '.'
curl -s http://localhost:5001/ | jq '.rate_limits'

# Redis monitoring (if used)
redis-cli info memory
redis-cli keys "flask_limiter:*"
```

---

**Deployment dengan optimization features dapat menghemat bandwidth hingga 90% dan meningkatkan user experience secara signifikan.**