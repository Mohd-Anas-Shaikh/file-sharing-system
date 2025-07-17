"""
WSGI entry point for the file sharing application
Used by Gunicorn for production deployment
"""

from app import app

if __name__ == "__main__":
    app.run()
