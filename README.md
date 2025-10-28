# Background Remover API

Aplikasi Flask untuk menghapus background dari gambar foto dengan fokus pada objek utama.

## ✨ Fitur

- 🖼️ **Multiple Input Methods**: File upload, preview, & base64 support
- 🚀 **Rate Limiting**: Perlindungan dari penyalahgunaan API
- 🔒 **Security**: File validation & CORS protection
- 🎯 **Background Removal**: Otomatis menggunakan rembg library
- 📁 **Multiple Formats**: PNG, JPG, JPEG, GIF, BMP, TIFF, WEBP
- 🧹 **Auto-cleanup**: File otomatis dihapus setelah 1 jam
- ⚙️ **Environment Config**: Konfigurasi mudah via .env file
- 🏥 **Health Check**: Monitoring API status

## 🚀 Quick Start

### 🎯 Automatic Setup (Recommended)

**Windows:**
```bash
# Run the setup script
setup.bat
```

**Linux/macOS:**
```bash
# Make script executable and run
chmod +x setup.sh
./setup.sh
```

### 🔧 Manual Setup

**Development:**
```bash
# 1. Copy environment template
cp .env.sample .env

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start development server
python app.py

# 4. Test API
curl http://localhost:5001/
```

**Production:**
```bash
# 1. Copy production config
cp .env.production .env

# 2. Customize sensitive values in .env
# 3. Install Redis for rate limiting
# 4. Start production server
python app.py
```

## 📡 API Endpoints

### Background Removal
| Method | Endpoint | Rate Limit | Description |
|--------|----------|------------|-------------|
| `POST` | `/remove-background` | 10/minute | Download file hasil |
| `POST` | `/remove-background-preview` | 15/minute | Preview di browser |
| `POST` | `/remove-background-base64` | 12/minute | Base64 input/output |

### System
| Method | Endpoint | Rate Limit | Description |
|--------|----------|------------|-------------|
| `GET` | `/` | 60/minute | API info & rate limits |
| `GET` | `/health` | 200/minute | Health check |

### 1. File Upload & Download
```bash
curl -X POST -F "file=@your_image.jpg" \
  http://localhost:5001/remove-background \
  --output result.png
```

### 2. Preview in Browser
```bash
curl -X POST -F "file=@your_image.jpg" \
  http://localhost:5001/remove-background-preview \
  --output preview.png
```

### 3. Base64 Processing
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"image":"base64_encoded_image"}' \
  http://localhost:5001/remove-background-base64
```

### 4. API Information
```bash
curl http://localhost:5001/
```

### 5. Health Check
```bash
curl http://localhost:5001/health
```

## Example Usage

### Menggunakan curl (File Upload)
```bash
curl -X POST -F "file=@your_image.jpg" http://127.0.0.1:5001/remove-background --output result.png
```

### Menggunakan curl (Base64)
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"image":"base64_encoded_image"}' \
  http://127.0.0.1:5001/remove-background-base64
```

### Menggunakan Python requests
```python
import requests

# Upload file
with open('your_image.jpg', 'rb') as f:
    response = requests.post(
        'http://127.0.0.1:5001/remove-background',
        files={'file': f}
    )

if response.status_code == 200:
    with open('result.png', 'wb') as f:
        f.write(response.content)
    print("Background removed successfully!")
```

## ⚙️ Konfigurasi

### Environment Variables (.env)
```bash
# Flask Configuration
DEBUG=True
HOST=0.0.0.0
PORT=5001

# Rate Limiting
RATE_LIMIT_REMOVE_BG_PER_MINUTE=10
RATE_LIMIT_PREVIEW_PER_MINUTE=15
RATE_LIMIT_BASE64_PER_MINUTE=12

# File Upload
MAX_CONTENT_LENGTH=16777216  # 16MB
```

### Rate Limiting
API dilindungi dengan rate limiting per endpoint:

- **Background Removal**: 10 requests/menit
- **Preview**: 15 requests/menit
- **Base64**: 12 requests/menit
- **Health**: 200 requests/menit
- **Info**: 60 requests/menit

Jika limit ter-exceed:
```json
{
  "error": "Rate limit exceeded",
  "message": "Too many requests. 10 per minute",
  "retry_after": "45"
}
```

## 📁 Supported Formats

### Input Formats
- ✅ PNG
- ✅ JPG/JPEG
- ✅ GIF
- ✅ BMP
- ✅ TIFF
- ✅ WEBP

### Output Format
- 📄 **Format**: PNG dengan transparansi
- 🎨 **Background**: Transparan
- 🖼️ **Object**: Dipertahankan dengan kualitas tinggi

## 🧪 Testing

### Test Web Interface
Buka `test.html` di browser untuk testing semua endpoints.

### Test Rate Limiting
```bash
# Test 15 requests (limit 10/minute)
for i in {1..15}; do
  curl -X POST -F "file=@test.jpg" \
    http://localhost:5001/remove-background
  echo "Request $i"
done
```

## 🚀 Production Deployment

Lihat `DEPLOYMENT.md` untuk lengkapnya:

```bash
# Copy production config
cp .env.production .env

# Install Redis untuk rate limiting storage
pip install redis

# Start production server
python app.py
```

## 📝 Notes

- 🧹 File otomatis dihapus setelah 1 jam
- ⏱️ Processing time tergantung ukuran gambar
- 🔒 Max file size: 16MB (configurable)
- 🌐 CORS enabled untuk all origins (configure di production)
- 📊 Rate limiting menggunakan memory storage (Redis untuk production)
- 🏥 Health check tersedia untuk monitoring

## 📄 Files

- `app.py` - Main application
- `.env` - Environment configuration (development)
- `.env.production` - Production configuration template
- `requirements.txt` - Python dependencies
- `test.html` - Web testing interface
- `DEPLOYMENT.md` - Deployment guide

---

## 🔧 Troubleshooting

**Rate limit tidak berfungsi?**
1. Restart server setelah ubah .env
2. Check Flask-Limiter installation
3. Verify environment variables

**File upload terlalu besar?**
1. Adjust `MAX_CONTENT_LENGTH` di .env
2. Check client upload limits

**CORS issues?**
1. Set `CORS_ORIGINS` ke domain yang benar
2. Check preflight OPTIONS requests
