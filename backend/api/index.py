
import sys
from pathlib import Path

# Locate the backend folder
PROJECT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_DIR / "backend"

# Allow Python to import backend modules
sys.path.insert(0, str(BACKEND_DIR))

# Import the existing Flask application
from app import app
