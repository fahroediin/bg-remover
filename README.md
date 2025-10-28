# Background Remover API

A powerful Flask-based API for removing backgrounds from images with advanced features including rate limiting, comprehensive logging, and multiple input methods.

## 🚀 Features

### Core Functionality
- **Background Removal**: High-quality background removal using rembg library
- **Multiple Input Methods**:
  - File upload (preview and download)
  - Base64 string input
  - File path support for local .txt files containing base64 data
- **Smart Validation**: Comprehensive input validation with PIL verification
- **Error Handling**: Detailed error messages and solutions

### User Interface
- **Clean, Modern Design**: Natural, non-AI-generated appearance
- **Two Tab Interface**: Preview and Base64 processing
- **Progress Indicators**: Animated progress bars during processing
- **Responsive Design**: Works on desktop and mobile devices
- **Interactive Elements**: Drag & drop file upload, click-to-browse

### Security & Performance
- **Rate Limiting**: Prevent API abuse with configurable limits
- **Input Validation**: Multiple layers of validation for security
- **Logging**: Comprehensive access and error logging
- **Environment Configuration**: Secure configuration management

## 📋 API Endpoints

| Method | Endpoint | Description | Rate Limit |
|--------|----------|-------------|------------|
| POST | `/remove-background` | Upload file, download result | 10/hour |
| POST | `/remove-background-preview` | Upload file, preview in browser | 20/hour |
| POST | `/remove-background-base64` | Process base64 image data | 30/hour |
| POST | `/read-file` | Read base64 from file path | 15/hour |
| GET | `/health` | Health check | 100/hour |
| GET | `/` | API information | 50/hour |

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.8+
- pip package manager

### Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd bg-remover
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.sample .env
   # Edit .env with your configuration
   ```

4. **Run the application**
   ```bash
   python app.py
   ```

5. **Access the application**
   - API: http://localhost:5001
   - Web Interface: http://localhost:5001

### Environment Configuration

Key environment variables (.env file):

```env
# Application
APP_NAME=Background Remover API
APP_VERSION=1.0.0
HOST=0.0.0.0
PORT=5001
DEBUG=False

# Rate Limiting
RATE_LIMIT_STORAGE=redis
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=INFO
LOG_FILE=bg_remover.log

# Security
CORS_ORIGINS=*
MAX_CONTENT_LENGTH=16777216
```

## 🎯 Usage Examples

### 1. File Upload with Preview
```bash
curl -X POST \
  http://localhost:5001/remove-background-preview \
  -H 'Content-Type: multipart/form-data' \
  -F 'file=@your-image.jpg'
```

### 2. Base64 Processing
```bash
curl -X POST \
  http://localhost:5001/remove-background-base64 \
  -H 'Content-Type: application/json' \
  -d '{
    "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  }'
```

### 3. File Path Processing (Web Interface)
1. Open the web interface
2. Go to Base64 tab
3. Enter file path: `C:\Users\User\Downloads\encoded-data.txt`
4. Click "Remove Background"

## 📁 Project Structure

```
bg-remover/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── .env.sample           # Environment template
├── .gitignore            # Git ignore rules
├── README.md             # This file
├── DOCS.md               # Technical documentation
├── index.html            # Web interface
├── static/
│   ├── css/
│   │   └── style.css     # Styling
│   └── js/
│       └── app.js        # Frontend logic
├── uploads/              # Temporary upload directory
├── outputs/              # Generated output directory
└── logs/                 # Log files directory
```

## 🔧 Configuration

### Rate Limiting
- **Preview**: 20 requests per hour
- **Base64**: 30 requests per hour
- **File Download**: 10 requests per hour
- **File Reading**: 15 requests per hour

### Supported Image Formats
- PNG, JPG/JPEG, GIF, BMP, TIFF, WEBP
- Maximum file size: 16MB
- Base64 strings with data URI scheme

### File Path Support
- Windows: `C:\Users\User\Downloads\encoded-data.txt`
- Linux/Mac: `/home/user/encoded-data.txt`
- Only .txt files are allowed for security

## 🚨 Error Handling

The API provides detailed error messages:

```json
{
  "error": "Invalid image file: Unsupported image format",
  "solution": "Please use a supported image format: PNG, JPG, GIF, BMP, TIFF, WEBP"
}
```

Common error types:
- File format validation
- Size limit validation
- Base64 format validation
- Network connectivity issues

## 📊 Logging

Comprehensive logging system tracks:
- API access with IP and User-Agent
- Processing success/failure rates
- Error details and resolutions
- Performance metrics

Log format:
```
2025-10-28 11:13:15 - INFO - API_ACCESS | 2025-10-28 11:13:15 | GET index | IP: 127.0.0.1 | UA: Mozilla/5.0...
2025-10-28 11:13:15 - INFO - API_SUCCESS | 2025-10-28 11:13:15 | POST base64 | IP: 127.0.0.1 | Status: 200
```

## 🔒 Security Features

- **Input Validation**: Multiple layers of validation
- **File Type Restrictions**: Only image files allowed
- **Path Validation**: Secure file path handling
- **Size Limits**: Configurable file size restrictions
- **Rate Limiting**: Prevents API abuse
- **CORS Configuration**: Configurable cross-origin policies

## 🐳 Docker Support

Create a `Dockerfile` for containerized deployment:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5001
CMD ["python", "app.py"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Check the logs for detailed error information
- Review the technical documentation (DOCS.md)
- Verify environment configuration
- Ensure all dependencies are installed

## 🔄 Updates

- **v1.0.0**: Initial release with core functionality
- Added progress bars and improved UI
- Enhanced base64 processing without original image display
- Fixed auto-refresh issues
- Added comprehensive file path support

---

**Built with ❤️ using Flask, rembg, and modern web technologies**