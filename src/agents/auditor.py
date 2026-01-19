import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.tools.tool_adapter import read_file, run_pylint
from src.config import DEFAULT_MODEL, DEV_MODE, MOCK_AUDIT_RESPONSE
from src.utils.llm_helper import call_gemini_with_retry

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


def clean_json_response(response: str) -> str:
    """
    Nettoie la réponse du LLM pour extraire le JSON pur.
    
    Args:
        response: Réponse brute du LLM
        
    Returns:
        JSON nettoyé (sans markdown)
    """
    response_clean = response.strip()
    
    # Enlever les balises markdown si présentes
    if "```json" in response_clean:
        # Format: ```json\n{...}\n```
        response_clean = response_clean.split("```json")[1].split("```")[0].strip()
    elif "```" in response_clean:
        # Format: ```\n{...}\n```
        parts = response_clean.split("```")
        if len(parts) >= 3:
            response_clean = parts[1].strip()
        elif len(parts) == 2:
            # Parfois juste ``` au début sans fermeture
            response_clean = parts[1].strip()
    
    # Enlever tout texte avant le premier {
    if "{" in response_clean:
        first_brace = response_clean.find("{")
        response_clean = response_clean[first_brace:]
    
    # Enlever tout texte après le dernier }
    if "}" in response_clean:
        last_brace = response_clean.rfind("}")
        response_clean = response_clean[:last_brace + 1]
    
    return response_clean


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
            print(f"📄 Analyzing: {filepath}")
    
            # Read file (relative path for file tools)
            code_content = read_file(filepath)
            if code_content:
                all_code += f"\n\n# Fichier: {filepath}\n{code_content}\n"
            
            # Run pylint (needs full path from sandbox root)
            full_path = os.path.join(target_dir, filepath)
            pylint_result = run_pylint(full_path)
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
        
        # Create intelligent mock for DEV mode
        if DEV_MODE:
            mock_audit = MOCK_AUDIT_RESPONSE
        else:
            mock_audit = None
            
        audit_report_raw = call_gemini_with_retry(
            full_prompt, 
            model_name=DEFAULT_MODEL,
            mock_response=mock_audit
        )
        
        # Clean the JSON response
        audit_report_clean = clean_json_response(audit_report_raw)
        
        # Validate JSON
        try:
            json_data = json.loads(audit_report_clean)
            print(f"✅ JSON valide parsé ({len(json_data.get('problemes', []))} problèmes détectés)")
            
            # Verify required fields
            required_fields = ["score_qualite", "problemes", "resume"]
            missing_fields = [f for f in required_fields if f not in json_data]
            
            if missing_fields:
                print(f"⚠️  Champs manquants dans le JSON: {missing_fields}")
                # Add default values
                if "score_qualite" not in json_data:
                    json_data["score_qualite"] = 5.0
                if "problemes" not in json_data:
                    json_data["problemes"] = []
                if "resume" not in json_data:
                    json_data["resume"] = "Analyse partielle"
                
                # Re-serialize with defaults
                audit_report_clean = json.dumps(json_data, ensure_ascii=False, indent=2)
            
            # Use cleaned version
            audit_report = audit_report_clean
            
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON invalide du LLM: {e}")
            print(f"📄 Réponse brute (premiers 300 chars): {audit_report_raw[:300]}")
            print(f"📄 Réponse nettoyée (premiers 300 chars): {audit_report_clean[:300]}")
            
            # Create fallback JSON
            fallback_json = {
                "score_qualite": 5.0,
                "problemes": [{
                    "fichier": python_files[0] if python_files else "unknown.py",
                    "ligne": 1,
                    "type": "general",
                    "severite": "majeur",
                    "description": "Erreur parsing réponse LLM - analyse manuelle requise",
                    "suggestion": "Vérifier le rapport brut dans les logs"
                }],
                "resume": "Erreur de parsing - rapport incomplet"
            }
            audit_report = json.dumps(fallback_json, ensure_ascii=False, indent=2)
            print(f"⚠️  Utilisation d'un rapport fallback")
        
        # Log this interaction
        log_experiment(
            agent_name="Auditor",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.ANALYSIS,
            details={
                "files_analyzed": python_files,
                "input_prompt": full_prompt[:1000] + "..." if len(full_prompt) > 1000 else full_prompt,
                "output_response": audit_report[:1000] + "..." if len(audit_report) > 1000 else audit_report,
                "pylint_scores": pylint_results,
                "code_length": len(all_code),
                "dev_mode": DEV_MODE,
                "used_prompt_builder": USE_PROMPT_BUILDER,
                "json_valid": True
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