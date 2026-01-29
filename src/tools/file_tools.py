from pathlib import Path
import os

# Le SANDBOX_ROOT sera défini dynamiquement
_SANDBOX_ROOT = None

def set_sandbox_root(target_dir: str):
    """
    Définit le dossier sandbox racine.
    Doit être appelé au début de l'exécution.
    """
    global _SANDBOX_ROOT
    _SANDBOX_ROOT = Path(target_dir).resolve()

def get_sandbox_root() -> Path:
    """Récupère le SANDBOX_ROOT actuel."""
    if _SANDBOX_ROOT is None:
        # Fallback par défaut
        return Path("sandbox/target").resolve()
    return _SANDBOX_ROOT

'--------------------------------------------------------------------------------------------'
def resolve_safe_path(relative_path: str) -> Path:
    sandbox_root = get_sandbox_root()
    path = (sandbox_root / relative_path).resolve()
    if not path.is_relative_to(sandbox_root):
        raise PermissionError("Access outside sandbox is forbidden")
    return path

'----------------------------------------------------------------------------------------------'
def read_file(relative_path: str) -> dict:
    try:
        path = resolve_safe_path(relative_path)
        if not path.exists():
            return {"success": False, "error": "File does not exist"}
        if not path.is_file():
            return {"success": False, "error": "Not a file"}
        return {
            "success": True,
            "content": path.read_text(encoding="utf-8")
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

'---------------------------------------------------------------------------------------'
def write_file(relative_path: str, content: str) -> dict:
    try:
        path = resolve_safe_path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

'-----------------------------------------------------------------------------------------'
def list_files(relative_path: str = ".") -> dict:
    try:
        path = resolve_safe_path(relative_path)
        if not path.exists():
            return {"success": False, "error": "Path does not exist"}
        if not path.is_dir():
            return {"success": False, "error": "Not a directory"}
        
        sandbox_root = get_sandbox_root()
        files = [
            str(p.relative_to(sandbox_root))
            for p in path.rglob("*")
            if p.is_file()
        ]
        return {"success": True, "files": files}
    except Exception as e:
        return {"success": False, "error": str(e)}