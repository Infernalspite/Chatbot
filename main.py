import sys
import os

# Add backend directory to python path so that all imports inside backend resolve correctly
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

from backend.main import app
