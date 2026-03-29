"""
wsgi.py - WSGI entry point for production deployment (Render, Heroku, etc.)
This file is used by gunicorn to start the application.
"""
import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'backend'))

# Set production environment
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('DEBUG', 'False')

# Import eventlet and monkey patch
import eventlet
eventlet.monkey_patch()

# Import Flask and SocketIO for production WSGI
from flask import Flask
from flask_socketio import SocketIO
from backend.app import create_app
from backend.config import Config

# Create the Flask app
app = create_app()

# Wrap with SocketIO for production
socketio = SocketIO(app, cors_allowed_origins=Config.ALLOWED_ORIGINS, async_mode="eventlet")

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
