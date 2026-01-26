from pathlib import Path

SANDBOX_ROOT = Path("sandbox/target").resolve()

#--------------------------------------------------
def resolve_safe_path(relative_path: str) -> Path:
    path = (SANDBOX_ROOT / relative_path).resolve()

    if not path.is_relative_to(SANDBOX_ROOT):
        raise PermissionError("Access outside sandbox is forbidden")

    return path
#-----------------------------------------------------------------------------
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
    
#---------------------------------------------------------------------------
def write_file(relative_path: str, content: str) -> dict:
    try:
        path = resolve_safe_path(relative_path)

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        return {"success": True}

    except Exception as e:
        return {"success": False, "error": str(e)}

#______________________________________________________________________

def list_files(relative_path: str = ".") -> dict:
    try:
        path = resolve_safe_path(relative_path)

        if not path.exists():
            return {"success": False, "error": "Path does not exist"}

        if not path.is_dir():
            return {"success": False, "error": "Not a directory"}

        files = [
            str(p.relative_to(SANDBOX_ROOT))
            for p in path.rglob("*")
            if p.is_file()
        ]

        return {"success": True, "files": files}

    except Exception as e:
        return {"success": False, "error": str(e)}
    


