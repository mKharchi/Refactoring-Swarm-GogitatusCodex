import subprocess

def run_tests() -> dict:
    """
    Run automated tests on the sandbox target code using pytest.

    Returns:
        dict:
            - success (bool): Whether pytest executed correctly.
            - returncode (int): Pytest exit code (0 = all tests passed).
            - stdout (str): Pytest output.
            - stderr (str): Error output if any.
    """
    try:
        result = subprocess.run(
            ["pytest", "sandbox/target", "-q"],
            capture_output=True,
            text=True,
            timeout=60
        )

        return {
            "success": True,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Test execution timed out"}

    except Exception as e:
        return {"success": False, "error": str(e)}
