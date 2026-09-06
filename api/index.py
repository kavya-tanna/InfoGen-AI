"""Vercel serverless function entrypoint for FastAPI backend."""
import os
import sys

# Add backend directory to Python path
backend_path = os.path.join(os.path.dirname(__file__), "..", "backend")
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from app.main import app
