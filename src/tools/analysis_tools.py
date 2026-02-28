import re
import subprocess
import sys



def extract_pylint_score(output: str) -> float:
    """
    Extract numerical score from pylint output.
    Looks for pattern: "Your code has been rated at X.XX/10"
    """
    try:
        match = re.search(r'rated at ([\d.]+)/10', output)
        if match:
            return float(match.group(1))
        return 0.0
    except:
        return 0.0

# In analysis_tool.py, improve parse_pylint_messages:

def parse_pylint_messages(stdout: str) -> dict:
    """Parse pylint messages into categories."""
    errors = []
    warnings = []
    conventions = []
    
    for line in stdout.split('\n'):
        line = line.strip()
        if not line or line.startswith('*') or line.startswith('-'):
            continue
        
        # Look for pylint issue pattern: filename:line:col: CODE: message
        if ':' in line and ': C' in line:  # Convention
            conventions.append(line)
        elif ':' in line and ': E' in line:  # Error
            errors.append(line)
        elif ':' in line and ': W' in line:  # Warning
            warnings.append(line)
        elif ':' in line and ': R' in line:  # Refactor
            conventions.append(line)  # Treat refactor as convention
    
    return {
        "errors": errors,
        "warnings": warnings,
        "conventions": conventions
    }


def run_pylint(filepath:str) -> dict:
    try:
        # always invoke via the same Python interpreter to ensure the module exists
        result = subprocess.run(
            [sys.executable, "-m", "pylint", filepath, "--output-format=text"],
            capture_output=True,
            text=True,
            timeout=30
        )

        score = extract_pylint_score(result.stdout)
        messages = parse_pylint_messages(result.stdout)
        total_issues = (
            len(messages["errors"]) + 
            len(messages["warnings"]) + 
            len(messages["conventions"])
        )
        print(score)
        
        return {
            "success": True,
            "score": score,
            "errors": messages["errors"],
            "warnings": messages["warnings"],
            "conventions": messages["conventions"],
            "total_issues": total_issues,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Pylint timed out"}

    except FileNotFoundError:
        return {"success": False, "error": "Pylint not installed"}
    except Exception as e:
        return {"success": False, "error": str(e)}