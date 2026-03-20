# Schedule Sender - Deployment Guide

## Quick Start

### 1. Clone on your server

```bash
cd /home/user
git clone <your-repo-url> schedule-sender
cd schedule-sender
```

### 2. Run deployment script

```bash
chmod +x deploy.sh
sudo ./deploy.sh
```

This will:
- Create Python virtual environment
- Install dependencies
- Setup nginx reverse proxy
- Create systemd service
- Start the app

### 3. Add your environment variables

Edit `.env` with your credentials:

```bash
nano .env
```

Required variables:
- `ADMIN_USERNAME` - Login username
- `ADMIN_PASSWORD` - Login password
- `INFOBIP_API_KEY` - WhatsApp API key
- `INFOBIP_BASE_URL` - Infobip API base URL
- `INFOBIP_SENDER` - Registered WhatsApp sender number
- `TO_WHATSAPP` - Recipient WhatsApp number (digits only, no +)

### 4. Verify it's running

```bash
# Check service status
sudo systemctl status schedule-sender

# View logs
tail -f /var/log/schedule-sender/app.log

# Test the app
curl http://localhost:80
```

### 5. (Optional) Enable SSL/HTTPS

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo systemctl restart nginx
```

---

## File Structure

- `start_prod.sh` - Gunicorn startup script (runs on localhost:8000)
- `nginx.conf` - Nginx reverse proxy config (listens on port 80/443)
- `schedule-sender.service` - Systemd service file
- `deploy.sh` - Automated setup script
- `.env` - Environment variables (create from `.env.example`)

---

## Manual Setup (if deploy.sh fails)

```bash
# 1. Virtual environment & dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup .env
cp .env.example .env
nano .env

# 3. Install nginx
sudo apt update && sudo apt install -y nginx

# 4. Configure nginx
sudo cp nginx.conf /etc/nginx/sites-available/schedule-sender
sudo ln -sf /etc/nginx/sites-available/schedule-sender /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 5. Install systemd service
sudo mkdir -p /var/log/schedule-sender
sudo cp schedule-sender.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable schedule-sender
sudo systemctl start schedule-sender
```

---

## Troubleshooting

### App won't start
```bash
# Check logs
tail -50 /var/log/schedule-sender/app.log

# Run manually to see errors
source venv/bin/activate
python app.py
```

### Nginx errors
```bash
sudo nginx -t
sudo systemctl restart nginx
tail -f /var/log/nginx/error.log
```

### Can't access the app
```bash
# Check if service is running
sudo systemctl status schedule-sender

# Check if nginx is listening
sudo netstat -tlnp | grep nginx

# Check if port 80 is blocked by firewall
sudo ufw allow 80
sudo ufw allow 443
```

---

## Updating the app

```bash
cd /home/user/schedule-sender
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart schedule-sender
```
