"""
TEMPORARY MOCK TOOLS
These are placeholders until Tool Smith finishes the real implementations.
DO NOT USE IN PRODUCTION - FOR DEVELOPMENT ONLY
"""
import os
from typing import Optional, Dict

def read_file(filepath: str) -> Optional[str]:
    """MOCK: Read file - basic implementation"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Mock read_file error: {e}")
        return None

def write_file(filepath: str, content: str) -> bool:
    """MOCK: Write file - NO SECURITY CHECK YET"""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"Mock write_file error: {e}")
        return False

def run_pylint(filepath: str) -> Optional[Dict]:
    """MOCK: Pylint - returns fake data for now"""
    print(f"⚠️  MOCK PYLINT on {filepath}")
    return {
        "score": 5.0,
        "errors": [{"message": "Mock error", "line": 1}],
        "warnings": [],
        "conventions": [],
        "total_issues": 1,
        "raw_output": "Mock pylint output"
    }

def run_pytest(directory: str) -> Optional[Dict]:
    """MOCK: Pytest - returns fake data for now"""
    print(f"⚠️  MOCK PYTEST on {directory}")
    return {
        "passed": False,
        "total": 3,
        "passed_count": 1,
        "failed_count": 2,
        "output": "Mock test output: 2 failed, 1 passed",
        "failures": ["Test 1 failed", "Test 2 failed"]
    }