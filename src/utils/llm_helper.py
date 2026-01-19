"""
Helper functions for LLM API calls with retry logic.
Centralizes all Gemini API interactions to avoid code duplication.
"""
import time
import google.generativeai as genai
from google.api_core import exceptions
from src.config import DEFAULT_MODEL, MAX_RETRIES, DEV_MODE


def call_gemini_with_retry(
    prompt: str, 
    model_name: str = DEFAULT_MODEL, 
    max_retries: int = MAX_RETRIES,
    mock_response: str = None
) -> str:
    """
    Calls Gemini API with retry logic or returns mock in DEV_MODE.
    
    Implements exponential backoff and rate limit handling.
    In production, adds delays between calls to respect rate limits.
    
    Args:
        prompt: The prompt to send to the LLM
        model_name: Model identifier (e.g., 'gemini-2.0-flash-exp')
        max_retries: Maximum number of retry attempts
        mock_response: Response to return in DEV_MODE
    
    Returns:
        LLM response text
        
    Raises:
        Exception: If quota is exhausted or other API errors occur
    """
    if DEV_MODE:
        print("  🔧 MODE DEV - Réponse simulée")
        time.sleep(0.5)  # Simulate API delay
        
        # If no mock provided, return a generic one
        if mock_response is None:
            mock_response = "# Mock response in DEV mode"
        
        return mock_response
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            
            # Rate limit management: add delays between calls
            if attempt > 0:
                # Exponential backoff for retries
                wait_time = 10 * (2 ** (attempt - 1))  # 10s, 20s, 40s
                print(f"  ⏳ Retry {attempt + 1}/{max_retries} dans {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Normal delay between calls: 4s allows ~15 calls/minute
                time.sleep(7)
            
            # Make the API call
            response = model.generate_content(prompt)
            return response.text
            
        except exceptions.ResourceExhausted as e:
            print(f"  ⚠️  Rate limit atteint (tentative {attempt + 1}/{max_retries})")
            
            if attempt < max_retries - 1:
                # Long wait for rate limit: 60s per attempt
                wait_time = 60 * (attempt + 1)  # 60s, 120s, 180s
                print(f"  ⏱️  Attente de {wait_time}s avant retry...")
                time.sleep(wait_time)
            else:
                # Max retries reached
                print(f"  ❌ Quota épuisé après {max_retries} tentatives")
                print(f"  💡 Solutions:")
                print(f"     1. Activez DEV_MODE=True dans config.py")
                print(f"     2. Attendez 1-2 minutes avant de réessayer")
                print(f"     3. Vérifiez votre quota sur https://aistudio.google.com/")
                raise Exception(f"Quota épuisé après {max_retries} tentatives")
                
        except exceptions.InvalidArgument as e:
            # Invalid request (bad prompt, wrong parameters)
            print(f"  ❌ Requête invalide: {str(e)}")
            raise Exception(f"Requête invalide: {str(e)}")
            
        except exceptions.PermissionDenied as e:
            # API key issues
            print(f"  ❌ Erreur d'authentification: {str(e)}")
            print(f"  💡 Vérifiez votre clé API dans .env")
            raise Exception(f"Erreur d'authentification: {str(e)}")
            
        except Exception as e:
            # Other errors
            print(f"  ❌ Erreur inattendue: {type(e).__name__}: {str(e)}")
            raise Exception(f"Erreur Gemini: {str(e)}")
    
    raise Exception(f"Max retries ({max_retries}) reached without success")


def estimate_tokens(text: str) -> int:
    """
    Rough estimation of token count.
    
    Args:
        text: Text to estimate
        
    Returns:
        Estimated token count (rough approximation)
    """
    # Rough estimate: ~4 characters per token for English/code
    # ~2-3 characters per token for French
    return len(text) // 3


def truncate_for_context(text: str, max_tokens: int = 2000) -> str:
    """
    Truncates text to fit within token limits.
    
    Args:
        text: Text to truncate
        max_tokens: Maximum tokens allowed
        
    Returns:
        Truncated text with indicator if truncation occurred
    """
    estimated_tokens = estimate_tokens(text)
    
    if estimated_tokens <= max_tokens:
        return text
    
    # Calculate how many characters to keep
    max_chars = max_tokens * 3
    truncated = text[:max_chars]
    
    return truncated + f"\n\n... [Tronqué: {estimated_tokens - max_tokens} tokens supprimés]"