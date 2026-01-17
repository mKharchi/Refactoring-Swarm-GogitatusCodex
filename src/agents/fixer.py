import os
import time
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions

from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.tools.tool_adapter import read_file, write_file
from src.config import DEFAULT_MODEL, MAX_RETRIES, RETRY_DELAY, DEV_MODE

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
        # Mock response: return the same code with a comment
        return "# Code corrigé en mode DEV\npass"
    
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


def fixer_agent(state: AgentState) -> AgentState:
    """The Fixer Agent: Reads audit report and fixes code file by file."""
    print("\n🔧 === AGENT CORRECTEUR ACTIVÉ ===")
    print(f"🔄 Itération: {state['iteration_count']}")
    
    if DEV_MODE:
        print("🔧 MODE DÉVELOPPEMENT ACTIVÉ")
    
    try:
        target_dir = state["target_dir"]
        python_files = state["python_files"]
        audit_report = state.get("audit_report", "")
        
        if not audit_report:
            print("⚠️  Aucun rapport d'audit trouvé")
            state["changes_made"] = ["Aucun rapport d'audit disponible"]
            return state
        
        if not python_files:
            print("⚠️  Aucun fichier Python à corriger")
            state["changes_made"] = ["Aucun fichier Python trouvé"]
            return state
        
        changes_made = []
        fixed_code_dict = {}
        
        # Process each Python file
        for filepath in python_files:
            print(f"\n📝 Correction de: {filepath}")
            
            # Read original code
            original_code = read_file(filepath)
            if not original_code:
                error_msg = f"❌ Impossible de lire {filepath}"
                print(f"  {error_msg}")
                changes_made.append(error_msg)
                continue
            
            # Build prompt using optimized builder if available
            if USE_PROMPT_BUILDER:
                print("  📝 Utilisation du prompt builder optimisé")
                system_prompt, user_prompt = prompt_builder.construire_prompt_correcteur(
                    code_source=original_code,
                    nom_fichier=filepath,
                    rapport_audit=audit_report
                )
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                # Analyze and log prompt cost
                cout = prompt_builder.analyser_couts(system_prompt, user_prompt, "Fixer")
                print(f"  💰 Tokens estimés: ~{cout.get('tokens_total_input', 0)} entrée")
            else:
                # Fallback to simple prompt
                print("  ⚠️  Utilisation du prompt simple (fallback)")
                full_prompt = f"""Tu es un expert Python spécialisé en refactoring et correction de code.

RAPPORT D'AUDIT GLOBAL:
{audit_report}

FICHIER À CORRIGER: {filepath}
CODE ACTUEL:
```python
{original_code}
```

INSTRUCTIONS CRITIQUES:
1. Analyse le rapport d'audit et identifie les problèmes concernant CE fichier spécifique
2. Corrige TOUS les problèmes identifiés (bugs, PEP8, documentation manquante)
3. Ajoute des docstrings complètes pour toutes les fonctions et classes
4. Assure-toi que le code reste fonctionnel et garde la même logique
5. Retourne UNIQUEMENT le code Python corrigé, SANS explications, SANS markdown

IMPORTANT: 
- NE retourne QUE le code Python pur
- PAS de ```python``` ou autres balises markdown
- PAS d'explications avant ou après
- Juste le code corrigé complet
"""
            
            # Call Gemini to fix the code
            print(f"  🤖 Appel à Gemini ({DEFAULT_MODEL if not DEV_MODE else 'MOCK'})...")
            try:
                fixed_code_response = call_gemini_with_retry(full_prompt, model_name=DEFAULT_MODEL)
                
                # Clean the response (remove markdown if present)
                fixed_code = fixed_code_response.strip()
                
                # Remove markdown code blocks if present
                if "```python" in fixed_code:
                    fixed_code = fixed_code.split("```python")[1].split("```")[0].strip()
                elif "```" in fixed_code:
                    # Handle case where it's just ``` without language
                    parts = fixed_code.split("```")
                    if len(parts) >= 3:
                        fixed_code = parts[1].strip()
                
                # Verify we got actual code (basic sanity check)
                if not fixed_code or len(fixed_code) < 10:
                    raise Exception("Réponse du LLM vide ou trop courte")
                
                # Write fixed code to file
                write_success = write_file(filepath, fixed_code)
                
                if write_success:
                    fixed_code_dict[filepath] = fixed_code
                    change_summary = f"✅ {filepath}: Code corrigé ({len(original_code)} → {len(fixed_code)} chars)"
                    changes_made.append(change_summary)
                    print(f"  {change_summary}")
                    
                    # Log successful fix
                    log_experiment(
                        agent_name="Fixer",
                        model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
                        action=ActionType.FIX,
                        details={
                            "iteration": state["iteration_count"],
                            "file_fixed": filepath,
                            "input_prompt": full_prompt,
                            "output_response": fixed_code_response[:500] + "..." if len(fixed_code_response) > 500 else fixed_code_response,
                            "code_length_before": len(original_code),
                            "code_length_after": len(fixed_code),
                            "dev_mode": DEV_MODE,
                            "used_prompt_builder": USE_PROMPT_BUILDER
                        },
                        status="SUCCESS"
                    )
                else:
                    error_msg = f"❌ {filepath}: Échec de l'écriture du fichier"
                    changes_made.append(error_msg)
                    print(f"  {error_msg}")
                    
            except Exception as e:
                error_msg = f"❌ {filepath}: Erreur de correction - {str(e)}"
                print(f"  {error_msg}")
                changes_made.append(error_msg)
                
                # Log failed fix
                log_experiment(
                    agent_name="Fixer",
                    model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
                    action=ActionType.FIX,
                    details={
                        "iteration": state["iteration_count"],
                        "file_fixed": filepath,
                        "input_prompt": full_prompt[:500] + "..." if len(full_prompt) > 500 else full_prompt,
                        "output_response": f"ERROR: {str(e)}",
                        "error": str(e),
                        "dev_mode": DEV_MODE
                    },
                    status="FAILED"
                )
        
        # Update state
        state["fixed_code"] = fixed_code_dict
        state["changes_made"] = changes_made if changes_made else ["Aucun changement appliqué"]
        
        print(f"\n✅ Correction terminée: {len(changes_made)} fichiers traités")
        print(f"📊 Fichiers corrigés avec succès: {len(fixed_code_dict)}/{len(python_files)}")
        
        return state
        
    except Exception as e:
        print(f"❌ Erreur du correcteur: {str(e)}")
        
        log_experiment(
            agent_name="Fixer",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.FIX,
            details={
                "iteration": state.get("iteration_count", 0),
                "error": str(e),
                "input_prompt": "Failed before prompt creation",
                "output_response": ""
            },
            status="FAILED"
        )
        
        state["changes_made"] = [f"Erreur critique: {str(e)}"]
        return state