"""
wsgi.py - WSGI entry point for production deployment (Render, Heroku, etc.)
This file is used by gunicorn to start the application.
"""
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('DEBUG', 'False')

from backend.app import app

if __name__ == "__main__":
    app.run()
