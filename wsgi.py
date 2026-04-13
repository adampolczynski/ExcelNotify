#!/usr/bin/env python3
"""
WSGI entry point for production servers (Gunicorn, uWSGI, etc.)
"""
from app import app

# Gunicorn will look for 'application' by default
application = app

if __name__ == "__main__":
    # For testing WSGI directly
    application.run()
