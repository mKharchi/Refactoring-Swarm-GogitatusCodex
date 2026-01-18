"""Configuration for the Refactoring Swarm."""
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Model Configuration - Use the FULL model name with 'models/' prefix!
# Au lieu de gemini-flash-lite-latest
DEFAULT_MODEL = "gemini-2.0-flash-exp"  # Rate limit plus élevé

# Fallback models in order of preference
FALLBACK_MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-pro",
]

DEV_MODE = os.getenv('DEV_MODE', 'false').lower() == 'true'
# Mock response for development mode
MOCK_AUDIT_RESPONSE = """{
  "problems": [
    {
      "file": "example.py",
        "line": 10,
        "type": "bug",
        "severity": "critical",
        "description": "There is a null pointer dereference.",
        "suggestion": "Add a null check before dereferencing the pointer."
    }
    ]
}"""

# Rate limiting
MAX_RETRIES = 3
RETRY_DELAY = 60