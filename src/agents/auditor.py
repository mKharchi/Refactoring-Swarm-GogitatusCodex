import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions

from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.tools.mock_tools import read_file, run_pylint
from src.config import DEFAULT_MODEL, MAX_RETRIES, RETRY_DELAY , DEV_MODE, MOCK_AUDIT_RESPONSE
# Import the optimized prompt builder
try:
    from src.prompts.prompt_builder import prompt_builder
    USE_PROMPT_BUILDER = True
    print("✅ Utilisation du prompt builder optimisé")
except ImportError as e:
    USE_PROMPT_BUILDER = False
    print(f"⚠️  Prompt builder non disponible: {e}")

load_dotenv()
if not DEV_MODE:
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))


def call_gemini_with_retry(prompt: str, model_name: str = DEFAULT_MODEL, max_retries: int = MAX_RETRIES) -> str:
    """Calls Gemini API with retry logic or returns mock in DEV_MODE."""
    if DEV_MODE:
        print("🔧 MODE DÉVELOPPEMENT - Utilisation de réponse simulée")
        time.sleep(1)
        return MOCK_AUDIT_RESPONSE
    
    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return response.text
            
        except exceptions.ResourceExhausted as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (attempt + 1)
                print(f"⏱️  Rate limit atteint. Attente de {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise Exception(f"Quota épuisé après {max_retries} tentatives")
                
        except Exception as e:
            raise Exception(f"Erreur Gemini: {str(e)}")
    
    raise Exception("Max retries reached")


def auditor_agent(state: AgentState) -> AgentState:
    """The Auditor Agent: Analyzes code and creates a refactoring plan."""
    print("\n🔍 === AGENT AUDITEUR ACTIVÉ ===")
    
    if DEV_MODE:
        print("🔧 MODE DÉVELOPPEMENT ACTIVÉ")
    
    try:
        target_dir = state["target_dir"]
        python_files = state["python_files"]
        
        if not python_files:
            state["status"] = "failed"
            state["error_message"] = "No Python files found"
            return state
        
        # Read all code files
        all_code = ""
        pylint_results = []
        
        for filepath in python_files:
            print(f"📄 Analysing: {filepath}")
            
            code_content = read_file(filepath)
            if code_content:
                all_code += f"\n\n# Fichier: {filepath}\n{code_content}\n"
            
            pylint_result = run_pylint(filepath)
            if pylint_result:
                pylint_results.append({
                    "file": filepath,
                    "score": pylint_result["score"],
                    "issues": pylint_result["total_issues"]
                })
        
        # Calculate average pylint score
        avg_score = None
        if pylint_results:
            avg_score = sum(r["score"] for r in pylint_results) / len(pylint_results)
            state["pylint_score_before"] = avg_score
        
        # Build prompt using optimized builder
        if USE_PROMPT_BUILDER:
            print("📝 Utilisation du prompt builder optimisé")
            system_prompt, user_prompt = prompt_builder.construire_prompt_auditeur(
                code_source=all_code,
                nom_fichier=python_files[0] if python_files else "unknown.py",
                score_pylint=avg_score
            )
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Analyze and log prompt cost
            cout = prompt_builder.analyser_couts(system_prompt, user_prompt, "Auditor")
            print(f"💰 Tokens estimés: ~{cout.get('tokens_total_input', 0)} entrée, "
                  f"~{cout.get('tokens_total_output_estime', 0)} sortie")
        else:
            # Fallback to simple prompt
            print("⚠️  Utilisation du prompt simple (fallback)")
            full_prompt = f"""Tu es un expert Python. Analyse ce code et identifie les problèmes:

{all_code}

Retourne un rapport JSON avec les bugs, problèmes PEP8, et manques de documentation."""
        
        # Call Gemini
        print(f"🤖 Appel à Gemini ({DEFAULT_MODEL if not DEV_MODE else 'MOCK'})...")
        audit_report = call_gemini_with_retry(full_prompt, model_name=DEFAULT_MODEL)
        
        # Log this interaction
        log_experiment(
            agent_name="Auditor",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.ANALYSIS,
            details={
                "files_analyzed": python_files,
                "input_prompt": full_prompt,
                "output_response": audit_report,
                "pylint_scores": pylint_results,
                "code_length": len(all_code),
                "dev_mode": DEV_MODE,
                "used_prompt_builder": USE_PROMPT_BUILDER
            },
            status="SUCCESS"
        )
        
        # Update state
        state["audit_report"] = audit_report
        state["iteration_count"] = 1
        
        print("✅ Analyse de l'auditeur terminée")
        if avg_score:
            print(f"📊 Score Pylint moyen: {avg_score:.2f}/10")
        
        return state
        
    except Exception as e:
        print(f"❌ Erreur de l'auditeur: {str(e)}")
        
        log_experiment(
            agent_name="Auditor",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.ANALYSIS,
            details={
                "error": str(e),
                "input_prompt": "Failed before prompt creation",
                "output_response": ""
            },
            status="FAILED"
        )
        
        state["status"] = "failed"
        state["error_message"] = f"Auditor error: {str(e)}"
        return state