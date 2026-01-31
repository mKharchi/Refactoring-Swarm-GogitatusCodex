"""
Adapter layer for tools.
Converts dict returns to formats agents expect.
"""
from typing import Optional, Dict

# Import real tools
from src.tools.file_tools import read_file as _read_file
from src.tools.file_tools import write_file as _write_file
from src.tools.file_tools import list_files as _list_python_files
from src.tools.analysis_tools import run_pylint as _run_pylint
from src.tools.test_tools import (
    write_test_file as _write_test_file,
    run_pytest as _run_pytest,
    cleanup_test_files as _cleanup_test_files,
    validate_test_syntax as _validate_test_syntax,
)

# ==============================================================================
# FILE OPERATIONS
# ==============================================================================

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

# ==============================================================================
# CODE ANALYSIS
# ==============================================================================

def run_pylint(filepath: str) -> Optional[Dict]:
    """Wrapper for pylint - returns dict with score and issues."""
    result = _run_pylint(filepath)
    if result["success"]:
        return result
    else:
        print(f"⚠️  Pylint failed: {result.get('error', 'Unknown error')}")
        return None

# ==============================================================================
# TEST TOOLS
# ==============================================================================

def write_test_file(filepath: str, content: str) -> bool:
    """
    Écrit un fichier de test de manière sécurisée.
    
    Args:
        filepath: Chemin du fichier de test
        content: Contenu du test Python
    
    Returns:
        True si succès, False sinon
    """
    return _write_test_file(filepath, content)


def run_pytest(test_file_path: str, code_files: list = None) -> Dict:
    """
    Exécute pytest sur un fichier de test.
    
    Args:
        test_file_path: Chemin du fichier de test
        code_files: Liste des fichiers de code (optionnel)
    
    Returns:
        Dict avec résultats détaillés
    """
    return _run_pytest(test_file_path, code_files)


def cleanup_test_files(test_file_path: str) -> bool:
    """
    Nettoie les fichiers de test temporaires.
    
    Args:
        test_file_path: Chemin du fichier de test
    
    Returns:
        True si succès, False sinon
    """
    return _cleanup_test_files(test_file_path)


def validate_test_syntax(test_content: str) -> Dict:
    """
    Valide la syntaxe Python d'un test.
    
    Args:
        test_content: Contenu du test
    
    Returns:
        {"valid": bool, "error": str | None}
    """
    return _validate_test_syntax(test_content)

