"""Configuration for the Refactoring Swarm."""
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Model Configuration - Use the FULL model name with 'models/' prefix!
# Au lieu de gemini-flash-lite-latest

# Fallback models in order of preference
FALLBACK_MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.5-pro",
    "models/gemini-2.0-flash-exp",
    "models/gemini-2.0-flash",
    "models/gemini-2.0-flash-001",
    "models/gemini-2.0-flash-exp-image-generation",
    "models/gemini-2.0-flash-lite-001",
    "models/gemini-2.0-flash-lite",
    "models/gemini-2.0-flash-lite-preview-02-05",
    "models/gemini-2.0-flash-lite-preview",
    "models/gemini-exp-1206",
    "models/gemini-2.5-flash-preview-tts",
    "models/gemini-2.5-pro-preview-tts",
    "models/gemma-3-1b-it",
    "models/gemma-3-4b-it",
    "models/gemma-3-12b-it",
    "models/gemma-3-27b-it",
    "models/gemma-3n-e4b-it",
    "models/gemma-3n-e2b-it",
    "models/gemini-flash-latest",
    "models/gemini-flash-lite-latest",
    "models/gemini-pro-latest",
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.5-flash-image",
    "models/gemini-2.5-flash-preview-09-2025",
    "models/gemini-2.5-flash-lite-preview-09-2025",
    "models/gemini-3-pro-preview",
    "models/gemini-3-flash-preview",
    "models/gemini-3-pro-image-preview",
    "models/nano-banana-pro-preview",
    "models/gemini-robotics-er-1.5-preview",
    "models/gemini-2.5-computer-use-preview-10-2025",
    "models/deep-research-pro-preview-12-2025"
]
DEFAULT_MODEL ="models/gemma-3n-e4b-it"  # Rate limit plus élevé

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