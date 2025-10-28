#!/bin/bash

# Background Remover API - Production Deployment Script
# This script automates the deployment process for production environments

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_NAME="bg-remover"
APP_USER="bgremover"
APP_DIR="/opt/bg-remover"
SERVICE_NAME="bg-remover"
NGINX_SITE="/etc/nginx/sites-available/bg-remover"

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

# Detect OS
detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
    else
        error "Cannot detect operating system"
    fi
    log "Detected OS: $OS $VER"
}

# Update system packages
update_system() {
    log "Updating system packages..."
    apt update && apt upgrade -y
}

# Install system dependencies
install_dependencies() {
    log "Installing system dependencies..."

    # Core dependencies
    apt install -y python3 python3-pip python3-venv nginx redis-server curl wget git

    # Development tools
    apt install -y build-essential gcc g++

    # Security and monitoring
    apt install -y ufail2ban logrotate
}

# Create application user
create_user() {
    log "Creating application user..."

    if ! id "$APP_USER" &>/dev/null; then
        useradd -m -s /bin/bash "$APP_USER"
        log "Created user: $APP_USER"
    else
        warning "User $APP_USER already exists"
    fi
}

# Setup application directory
setup_directories() {
    log "Setting up application directories..."

    mkdir -p "$APP_DIR"
    mkdir -p "$APP_DIR/uploads"
    mkdir -p "$APP_DIR/outputs"
    mkdir -p "$APP_DIR/logs"
    mkdir -p "$APP_DIR/ssl"

    # Set permissions
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"
    chmod 755 "$APP_DIR/uploads" "$APP_DIR/outputs" "$APP_DIR/logs"

    log "Directories created and permissions set"
}

# Deploy application code
deploy_application() {
    log "Deploying application code..."

    # Copy application files (assuming running from project directory)
    cp -r . "$APP_DIR/"
    chown -R "$APP_USER:$APP_USER" "$APP_DIR"

    # Setup Python virtual environment
    sudo -u "$APP_USER" bash << EOF
cd $APP_DIR
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn
EOF

    log "Application deployed successfully"
}

# Setup environment configuration
setup_environment() {
    log "Setting up environment configuration..."

    if [[ ! -f "$APP_DIR/.env" ]]; then
        if [[ -f "$APP_DIR/.env.production" ]]; then
            cp "$APP_DIR/.env.production" "$APP_DIR/.env"
        else
            cp "$APP_DIR/.env.sample" "$APP_DIR/.env"
        fi

        # Generate secure secret key
        SECRET_KEY=$(openssl rand -hex 32)
        sudo -u "$APP_USER" sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$APP_DIR/.env"

        # Set production values
        sudo -u "$APP_USER" sed -i "s/DEBUG=.*/DEBUG=False/" "$APP_DIR/.env"
        sudo -u "$APP_USER" sed -i "s/REDIS_URL=.*/REDIS_URL=redis:\/\/localhost:6379\/0/" "$APP_DIR/.env"

        chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
        chmod 600 "$APP_DIR/.env"

        log "Environment configuration created"
    else
        warning "Environment file already exists"
    fi
}

# Setup systemd service
setup_systemd_service() {
    log "Setting up systemd service..."

    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Background Remover API
After=network.target redis.service

[Service]
Type=exec
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/gunicorn --config gunicorn.conf.py app:app
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$APP_DIR/uploads $APP_DIR/outputs $APP_DIR/logs

[Install]
WantedBy=multi-user.target
EOF

    # Create Gunicorn configuration
    sudo -u "$APP_USER" cat > "$APP_DIR/gunicorn.conf.py" << EOF
import multiprocessing

bind = "127.0.0.1:5001"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100
timeout = 120
keepalive = 2
preload_app = True
user = "$APP_USER"
group = "$APP_USER"
tmp_upload_dir = None
logconfig = None
accesslog = "-"
errorlog = "-"
EOF

    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    log "Systemd service configured"
}

# Setup Nginx
setup_nginx() {
    log "Setting up Nginx configuration..."

    # Get domain from user or use default
    read -p "Enter your domain name (default: localhost): " DOMAIN
    DOMAIN=${DOMAIN:-localhost}

    cat > "$NGINX_SITE" << EOF
server {
    listen 80;
    server_name $DOMAIN;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # File upload size limit
    client_max_body_size 16M;

    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Disable buffering for large file uploads
        proxy_request_buffering off;
    }

    # Static file serving
    location /static/ {
        alias $APP_DIR/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        proxy_pass http://127.0.0.1:5001/health;
        access_log off;
    }

    # Deny access to hidden files
    location ~ /\. {
        deny all;
    }
}
EOF

    # Enable site
    ln -sf "$NGINX_SITE" "/etc/nginx/sites-enabled/"

    # Remove default site
    rm -f "/etc/nginx/sites-enabled/default"

    # Test configuration
    nginx -t

    log "Nginx configured for domain: $DOMAIN"
}

# Setup SSL with Let's Encrypt (optional)
setup_ssl() {
    read -p "Do you want to setup SSL with Let's Encrypt? (y/n): " SETUP_SSL

    if [[ $SETUP_SSL =~ ^[Yy]$ ]]; then
        log "Setting up SSL with Let's Encrypt..."

        # Install Certbot
        apt install -y certbot python3-certbot-nginx

        # Get domain from nginx config
        DOMAIN=$(grep "server_name" "$NGINX_SITE" | awk '{print $2}' | head -1)

        # Request certificate
        certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email "admin@$DOMAIN"

        # Setup auto-renewal
        echo "0 12 * * * /usr/bin/certbot renew --quiet" | crontab -

        log "SSL certificate installed for $DOMAIN"
    fi
}

# Setup log rotation
setup_log_rotation() {
    log "Setting up log rotation..."

    cat > "/etc/logrotate.d/$SERVICE_NAME" << EOF
$APP_DIR/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $APP_USER $APP_USER
    postrotate
        systemctl reload $SERVICE_NAME
    endscript
}
EOF

    log "Log rotation configured"
}

# Setup monitoring and security
setup_monitoring() {
    log "Setting up monitoring and security..."

    # Configure Redis
    sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
    systemctl restart redis

    # Setup fail2ban for nginx
    cat > "/etc/fail2ban/jail.local" << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
EOF

    systemctl enable fail2ban
    systemctl start fail2ban

    log "Monitoring and security configured"
}

# Start services
start_services() {
    log "Starting services..."

    # Start Redis
    systemctl start redis
    systemctl enable redis

    # Start application
    systemctl start "$SERVICE_NAME"

    # Start Nginx
    systemctl restart nginx
    systemctl enable nginx

    log "All services started successfully"
}

# Health check
health_check() {
    log "Performing health check..."

    # Check if services are running
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        error "Application service is not running"
    fi

    if ! systemctl is-active --quiet nginx; then
        error "Nginx is not running"
    fi

    if ! systemctl is-active --quiet redis; then
        error "Redis is not running"
    fi

    # Check API health
    sleep 5
    if curl -f http://localhost:5001/health > /dev/null 2>&1; then
        log "API health check passed"
    else
        error "API health check failed"
    fi
}

# Setup cleanup script
setup_cleanup() {
    log "Setting up cleanup script..."

    cat > "/etc/cron.hourly/cleanup-$SERVICE_NAME" << EOF
#!/bin/bash
# Cleanup old files

# Remove files older than 1 hour
find $APP_DIR/uploads -type f -mtime +0 -delete
find $APP_DIR/outputs -type f -mtime +0 -delete

# Clean Redis rate limiting data (older than 1 day)
redis-cli --scan --pattern "flask_limiter:*" | xargs -r redis-cli del
EOF

    chmod +x "/etc/cron.hourly/cleanup-$SERVICE_NAME"

    log "Cleanup script configured"
}

# Print deployment summary
print_summary() {
    DOMAIN=$(grep "server_name" "$NGINX_SITE" | awk '{print $2}' | head -1)

    echo ""
    echo "==================================="
    echo "🎉 Deployment Complete!"
    echo "==================================="
    echo ""
    echo "📊 Application Details:"
    echo "  • Status: Running"
    echo "  • Domain: $DOMAIN"
    echo "  • API URL: http://$DOMAIN"
    echo "  • Health Check: http://$DOMAIN/health"
    echo ""
    echo "📁 Important Paths:"
    echo "  • Application: $APP_DIR"
    echo "  • Logs: $APP_DIR/logs"
    echo "  • Uploads: $APP_DIR/uploads"
    echo "  • Config: $APP_DIR/.env"
    echo ""
    echo "🔧 Management Commands:"
    echo "  • Restart app: sudo systemctl restart $SERVICE_NAME"
    echo "  • View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "  • Restart nginx: sudo systemctl restart nginx"
    echo "  • Check Redis: redis-cli ping"
    echo ""
    echo "📝 Next Steps:"
    echo "  1. Configure your domain DNS to point to this server"
    echo "  2. Setup SSL certificate if not done automatically"
    echo "  3. Configure firewall to allow ports 80 and 443"
    echo "  4. Monitor application logs regularly"
    echo "  5. Set up backup for important files"
    echo ""
    echo "📚 Documentation:"
    echo "  • README: $APP_DIR/README.md"
    echo "  • Technical Docs: $APP_DIR/DOCS.md"
    echo ""
}

# Main deployment function
main() {
    echo "==================================="
    echo "🚀 Background Remover API Deployment"
    echo "==================================="
    echo ""

    check_root
    detect_os

    read -p "This will deploy the Background Remover API to production. Continue? (y/n): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        log "Deployment cancelled"
        exit 0
    fi

    log "Starting deployment process..."

    update_system
    install_dependencies
    create_user
    setup_directories
    deploy_application
    setup_environment
    setup_systemd_service
    setup_nginx
    setup_ssl
    setup_log_rotation
    setup_monitoring
    start_services
    health_check
    setup_cleanup
    print_summary

    log "Deployment completed successfully!"
}

# Run main function
main "$@"