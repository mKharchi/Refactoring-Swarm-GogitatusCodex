import subprocess

def run_pylint() -> dict:
    try:
        result = subprocess.run(
            ["pylint", "sandbox/target"],
            capture_output=True,
            text=True,
            timeout=30
        )

        return {
            "success": True,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Pylint timed out"}

    except Exception as e:
        return {"success": False, "error": str(e)}