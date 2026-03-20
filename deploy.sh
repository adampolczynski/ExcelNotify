#!/bin/bash
# Deploy script for Schedule Sender on Ubuntu/Debian
# Run this ONCE on the server after cloning the repo

set -e

echo "======================================"
echo "Schedule Sender - Server Setup"
echo "======================================"

PROJECT_DIR=$(pwd)
VENV_DIR="$PROJECT_DIR/venv"
APP_USER="root"

# 1. Create virtual environment
echo "[1/7] Creating virtual environment..."
python3 -m venv $VENV_DIR
source $VENV_DIR/bin/activate

# 2. Install dependencies
echo "[2/7] Installing Python dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# 3. Setup .env file
echo "[3/7] Setting up .env file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚠️  Edit .env with your credentials:"
    echo "   - ADMIN_USERNAME"
    echo "   - ADMIN_PASSWORD"
    echo "   - INFOBIP_API_KEY"
    echo "   - INFOBIP_BASE_URL"
    echo "   - INFOBIP_SENDER"
    echo "   - TO_WHATSAPP"
    read -p "Press Enter when done editing .env"
fi

# 4. Install nginx
echo "[4/7] Installing nginx..."
sudo apt update -qq
sudo apt install -y -qq nginx

# 5. Configure nginx
echo "[5/7] Configuring nginx..."
sudo cp nginx.conf /etc/nginx/sites-available/schedule-sender
sudo ln -sf /etc/nginx/sites-available/schedule-sender /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 6. Create log directory
echo "[6/7] Creating log directory..."
sudo mkdir -p /var/log/schedule-sender
sudo chown $APP_USER:$APP_USER /var/log/schedule-sender

# 7. Install systemd service
echo "[7/7] Installing systemd service..."
sudo cp schedule-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable schedule-sender
sudo systemctl start schedule-sender

# Setup SSL with certbot (optional)
echo ""
echo "======================================"
echo "Setup Complete!"
echo "======================================"
echo ""
echo "Optional: Enable SSL/HTTPS"
echo "  sudo apt install -y certbot python3-certbot-nginx"
echo "  sudo certbot --nginx -d your-domain.com"
echo "  sudo systemctl restart nginx"
echo ""
echo "Check status:"
echo "  sudo systemctl status schedule-sender"
echo "  tail -f /var/log/schedule-sender/app.log"
echo ""
