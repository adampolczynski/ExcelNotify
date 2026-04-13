# Gunicorn configuration for production
import multiprocessing
import os

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
timeout = 30
keepalive = 2

# Restart workers after this many requests, with a randomized offset
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"

# Process naming
proc_name = "schedule_sender"

# Server mechanics
daemon = False
pidfile = "/tmp/gunicorn.pid"
user = None
group = None
tmp_upload_dir = None

# SSL (uncomment and configure if needed)
# keyfile = "/path/to/ssl/private.key"
# certfile = "/path/to/ssl/certificate.crt"

# Application
wsgi_module = "wsgi:application"
pythonpath = "/home/beat/Code/web/project"

# Worker timeout
graceful_timeout = 30

# Preload application
preload_app = True
