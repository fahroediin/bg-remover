#!/bin/bash

# Background Remover API - Setup Script
# This script helps you set up the environment quickly

set -e

echo "🚀 Background Remover API - Setup Script"
echo "========================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env file exists
if [ -f ".env" ]; then
    print_warning ".env file already exists!"
    read -p "Do you want to overwrite it? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Keeping existing .env file"
    else
        cp .env.sample .env
        print_success "Created new .env from .env.sample"
    fi
else
    cp .env.sample .env
    print_success "Created .env file from .env.sample"
fi

# Check Python installation
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python is not installed. Please install Python 3.8 or higher."
    exit 1
fi

# Determine Python command
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

print_status "Using Python command: $PYTHON_CMD"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    print_status "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
else
    print_status "Virtual environment already exists"
fi

# Activate virtual environment
print_status "Activating virtual environment..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || {
    print_error "Failed to activate virtual environment"
    exit 1
}

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
print_status "Installing dependencies..."
pip install -r requirements.txt

print_success "Dependencies installed successfully!"

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads outputs temp
print_success "Directories created"

# Check if Redis is available (optional)
if command -v redis-server &> /dev/null; then
    print_success "Redis is available for production rate limiting"
else
    print_warning "Redis is not installed. Rate limiting will use memory storage."
    print_status "Install Redis for production: https://redis.io/download"
fi

# Test the setup
print_status "Testing setup..."
$PYTHON_CMD -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('✅ Environment variables loaded successfully')
print('✅ Rate limiting configuration:', os.getenv('RATE_LIMIT_STORAGE', 'memory'))
print('✅ Flask configuration loaded')
" 2>/dev/null || {
    print_error "Setup test failed"
    exit 1
}

print_success "Setup test passed!"

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "Next steps:"
echo "1. Review and customize your .env file if needed"
echo "2. Start the server: $PYTHON_CMD app.py"
echo "3. Open your browser to test: http://localhost:5001"
echo "4. Or use the test.html file for easy testing"
echo ""
echo "For production deployment:"
echo "1. Copy .env.production to .env"
echo "2. Install and configure Redis"
echo "3. Update CORS_ORIGINS in .env"
echo "4. Set DEBUG=False"
echo ""
echo "Happy coding! 🚀"