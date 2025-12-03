#!/bin/bash
# Startup script for social-links-flask service

# Change to project directory
cd /home/root01/links-scraper-v2

# Activate virtual environment
source venv/bin/activate

# Start the Flask application
python3 app.py
