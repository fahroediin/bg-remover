# Background Remover API - Production Docker Image
FROM python:3.9-slim

# Set metadata
LABEL maintainer="Background Remover Team"
LABEL version="1.0.0"
LABEL description="Background Remover API with Flask and rembg"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    DEBUG=False \
    APP_DIR=/app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR $APP_DIR

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir gunicorn

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads outputs logs static && \
    chown -R appuser:appuser $APP_DIR && \
    chmod 755 uploads outputs logs

# Copy production environment file
RUN if [ -f .env.production ]; then cp .env.production .env; fi

# Set permissions
RUN chmod +x deploy.sh 2>/dev/null || true

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# Expose port
EXPOSE 5001

# Run the application
CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]