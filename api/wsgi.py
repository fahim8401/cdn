#!/usr/bin/env python3
"""
Cachenet CDN Platform WSGI Entry Point
Production WSGI server configuration
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the application directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask application
from app import app

# Configure for production
application = app

if __name__ == "__main__":
    application.run()