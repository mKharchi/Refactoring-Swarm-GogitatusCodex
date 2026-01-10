import os
import google.generativeai as genai
from dotenv import load_dotenv
from src.config import DEFAULT_MODEL , FALLBACK_MODELS , MAX_RETRIES , RETRY_DELAY

from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.tools.mock_tools import read_file, run_pylint  # TEMPORARY - use mock tools

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))


def load_auditor_prompt() -> str:
    """Load the current auditor prompt from file"""
    prompt_path = "src/prompts/system_prompts/auditor_current_prompt.txt"
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"⚠️  Could not load prompt from {prompt_path}: {e}")
        # Fallback prompt
        return """Tu es un expert Senior en Python et en Clean Code.
Ta mission est d'analyser le code qu'on te donne.
Tu dois identifier :
1. Les bugs potentiels.
2. Le non-respect des normes PEP8.
3. Le manque de documentation."""


def auditor_agent(state: AgentState) -> AgentState:
    """
    The Auditor Agent: Analyzes code and creates a refactoring plan.
    """
    print("\n🔍 === AGENT AUDITEUR ACTIVÉ ===")
    
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
            print(f"📄 Analyzing: {filepath}")
            
            # Read file
            code_content = read_file(filepath)
            if code_content:
                all_code += f"\n\n# Fichier: {filepath}\n{code_content}\n"
            
            # Run pylint (mock for now)
            pylint_result = run_pylint(filepath)
            if pylint_result:
                pylint_results.append({
                    "file": filepath,
                    "score": pylint_result["score"],
                    "issues": pylint_result["total_issues"]
                })
        
        # Calculate average pylint score
        if pylint_results:
            avg_score = sum(r["score"] for r in pylint_results) / len(pylint_results)
            state["pylint_score_before"] = avg_score
        
        # Load system prompt
        system_prompt = load_auditor_prompt()
        
        # Build user prompt
        user_prompt = f"""Analyse le code Python suivant et crée un plan de refactoring détaillé.

{all_code}

Pour chaque problème identifié, précise :
- Le type de problème (bug, PEP8, documentation)
- L'emplacement (fichier et ligne si possible)
- La gravité (Critique/Haute/Moyenne/Basse)
- Une recommandation de correction

Fournis ensuite un plan de refactoring priorisé par gravité."""
        
        # Call Gemini
        model = genai.GenerativeModel(DEFAULT_MODEL)
        
        
        print("🤖 Appel à Gemini pour l'analyse...")
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = model.generate_content(full_prompt)
        
        audit_report = response.text
        
        # Log this interaction (CRITICAL!)
        log_experiment(
            agent_name="Auditor",
            model_used="gemini-2.0-flash-exp",
            action=ActionType.ANALYSIS,
            details={
                "files_analyzed": python_files,
                "input_prompt": full_prompt,
                "output_response": audit_report,
                "pylint_scores": pylint_results,
                "code_length": len(all_code)
            },
            status="SUCCESS"
        )
        
        # Update state
        state["audit_report"] = audit_report
        state["iteration_count"] = 1
        
        print("✅ Analyse de l'auditeur terminée")
        print(f"📊 Score Pylint moyen: {state.get('pylint_score_before', 0):.2f}/10")
        
        return state
        
    except Exception as e:
        print(f"❌ Erreur de l'auditeur: {str(e)}")
        
        log_experiment(
            agent_name="Auditor",
            model_used=DEFAULT_MODEL,
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