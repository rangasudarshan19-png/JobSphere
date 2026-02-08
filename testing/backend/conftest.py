"""
Backend Tests: Initialize conftest
"""
import sys
from pathlib import Path

# Add backend to Python path for test imports
backend_path = Path(__file__).parent.parent.parent / "backend" / "python-service"
sys.path.insert(0, str(backend_path))
