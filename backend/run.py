#!/usr/bin/env python
"""
run.py - Production entry point for Render
Ensures eventlet monkey_patch is called FIRST, before any other imports.
"""

# MUST be first line - before any other imports!
import eventlet
eventlet.monkey_patch()

# Now we can import the app
import os
import sys

# Set production mode
os.environ.setdefault('FLASK_ENV', 'production')
os.environ.setdefault('DEBUG', 'False')

sys.path.insert(0, os.path.dirname(__file__))

from app import socketio, app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting SocketIO server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
