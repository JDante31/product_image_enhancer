"""
Utility functions for path handling and directory management.
"""

from pathlib import Path

def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.parent

def get_data_path(subdir: str = '') -> Path:
    """Get the path to a data subdirectory, creating it if it doesn't exist."""
    data_path = get_project_root() / 'data' / subdir
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path 