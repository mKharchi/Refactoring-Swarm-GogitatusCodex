"""Configuration for the Refactoring Swarm."""
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

# Model Configuration - Use the FULL model name with 'models/' prefix!
DEFAULT_MODEL = "models/gemini-flash-lite-latest"


# Fallback models in order of preference
FALLBACK_MODELS = [
    "models/gemini-2.5-flash",
    "models/gemini-2.0-flash",
    "models/gemini-2.5-pro",
]

# Rate limiting
MAX_RETRIES = 3
RETRY_DELAY = 60