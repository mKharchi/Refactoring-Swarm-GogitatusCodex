"""
Adapter layer for tools.
Converts dict returns to formats agents expect.
"""
from typing import Optional, Dict

# Import real tools (now with your enhancements)
from src.tools.file_tools import read_file as _read_file
from src.tools.file_tools import write_file as _write_file
from src.tools.file_tools import list_files as _list_python_files
from src.tools.analysis_tools import run_pylint as _run_pylint
from src.tools.test_tools_mock import (
    write_test_file,
    run_pytest,
    cleanup_test_files,
    validate_test_syntax
)

def read_file(filepath: str) -> Optional[str]:
    """Simple wrapper: returns content or None."""
    result = _read_file(filepath)
    if result["success"]:
        return result["content"]
    else:
        print(f"⚠️  Read failed: {result.get('error', 'Unknown error')}")
        return None


def write_file(filepath: str, content: str) -> bool:
    """Simple wrapper: returns True/False."""
    result = _write_file(filepath, content)
    if result["success"]:
        return True
    else:
        print(f"⚠️  Write failed: {result.get('error', 'Unknown error')}")
        return False


def list_python_files(directory: str = ".") -> list[str]:
    """Simple wrapper: returns list of files."""
    result = _list_python_files(directory)
    if result["success"]:
        return result["files"]
    else:
        print(f"⚠️  List failed: {result.get('error', 'Unknown error')}")
        return []


def run_pylint(filepath: str) -> Optional[Dict]:
    """Wrapper for pylint - returns dict with score and issues."""
    result = _run_pylint(filepath)
    
    if result["success"]:
        return result  # Already in correct format
    else:
        print(f"⚠️  Pylint failed: {result.get('error', 'Unknown error')}")
        return None

