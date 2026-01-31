import os
import time
import json
import google.generativeai as genai
from dotenv import load_dotenv
from google.api_core import exceptions

from src import state
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


def extraire_problemes_fichier(audit_report: str, filepath: str) -> list:
    """
    Extrait les problèmes concernant un fichier spécifique du rapport d'audit.
    
    Args:
        audit_report: Le rapport d'audit complet (peut être JSON ou texte)
        filepath: Le nom du fichier à filtrer
    
    Returns:
        Liste des problèmes pour ce fichier
    """
    try:
        # Essayer de parser le rapport comme JSON
        data = json.loads(audit_report)
        
        # Si c'est la structure attendue avec "problemes"
        if isinstance(data, dict) and "problemes" in data:
            problemes = data["problemes"]
            # Filtrer pour ce fichier
            return [
                p for p in problemes 
                if p.get("fichier", "") == filepath or filepath in p.get("fichier", "")
            ]
        
        # Si c'est déjà une liste de problèmes
        elif isinstance(data, list):
            return [
                p for p in data 
                if p.get("fichier", "") == filepath or filepath in p.get("fichier", "")
            ]
    
    except (json.JSONDecodeError, KeyError):
        # Si ce n'est pas du JSON valide, créer un problème générique
        print(f"  ⚠️  Impossible de parser le rapport d'audit comme JSON")
        return [{
            "fichier": filepath,
            "ligne": 1,
            "type": "general",
            "severite": "majeur",
            "description": "Code nécessite refactoring général",
            "suggestion": "Voir rapport d'audit complet"
        }]
    
    # Si aucun problème trouvé pour ce fichier
    return [{
        "fichier": filepath,
        "ligne": 1,
        "type": "general",
        "severite": "mineur",
        "description": "Amélioration générale du code",
        "suggestion": "Ajouter documentation et respecter PEP8"
    }]

# Au début du fichier
from src.utils.llm_helper import call_gemini_with_retry

# SUPPRIMEZ la définition de call_gemini_with_retry
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
        # ========== NOUVEAU CODE ==========
# RÉCUPÉRER LE FEEDBACK DU JUDGE
        test_output = state.get("test_output", "")
        test_passed = state.get("test_passed", True)
        iteration = state.get("iteration_count", 1)

# Construire le contexte de feedback
        feedback_context = ""

        if iteration > 1 and test_output:
    # Extraire seulement les lignes d'erreur
            lignes_erreur = [
                    ligne for ligne in test_output.split('\n')
                    if any(mot in ligne for mot in [
                                'FAILED', 'ERROR', 'AssertionError', 
                                'TypeError', 'ValueError', 'NameError',
                                'File "', 'line ', '>>>'
                            ])
                    ]
    
            if lignes_erreur:
                feedback_context = f"""
╔══════════════════════════════════════════════════════════════════╗
║ ⚠️  ATTENTION - ITÉRATION {iteration}                                 ║
║ Les tests ont ÉCHOUÉ. Voici les erreurs PRÉCISES à corriger :    ║
╚══════════════════════════════════════════════════════════════════╝

ERREURS DE TESTS DÉTECTÉES :
{chr(10).join(lignes_erreur[:20])}

INSTRUCTIONS CRITIQUES POUR CETTE ITÉRATION :
1. 🎯 Analyse PRÉCISÉMENT ces erreurs (nom de fonction, ligne, type d'erreur)
2. 🚫 NE réécris PAS le code à l'identique - ça ne fonctionnera pas
3. 🔍 Concentre-toi sur les fonctions mentionnées dans les erreurs
4. ✅ Garde les parties du code qui fonctionnent déjà
5. 🧪 Assure-toi que les corrections résolvent les AssertionError
"""
            else:
                feedback_context = f"""
ITÉRATION {iteration} : Tests partiellement réussis.
Continue d'améliorer le code en te basant sur le rapport d'audit.
"""

        print(f"  📋 Feedback tests : {len(feedback_context)} caractères")
# ========== FIN DU NOUVEAU CODE ==========
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
                
                problemes_fichier = extraire_problemes_fichier(audit_report, filepath)
                
                system_prompt, user_prompt = prompt_builder.construire_prompt_correcteur(
        code_source=original_code,
        problemes=problemes_fichier,
        nom_fichier=filepath,
        feedback_tests=feedback_context
    )
                full_prompt = system_prompt + "\n\n" + user_prompt

            else:
                print("  ⚠️  Utilisation du prompt simple (fallback)")
                full_prompt = f"""Tu es un expert Python. Ton rôle est de corriger et améliorer du code Python.

FICHIER: {filepath}

{feedback_context}  # ← AJOUTER CETTE LIGNE

CODE ORIGINAL À CORRIGER:
{original_code}

PROBLÈMES DÉTECTÉS (Rapport d'audit):
{audit_report[:500] if len(audit_report) > 500 else audit_report}

INSTRUCTIONS:
1. Lis attentivement le code original ci-dessus
2. Corrige tous les bugs et problèmes identifiés
3. Ajoute des docstrings Google-style pour toutes les fonctions et classes
4. Assure-toi que le code respecte PEP 8
5. Garde exactement la même fonctionnalité

IMPORTANT - FORMAT DE RÉPONSE:
- Retourne TOUT le code corrigé du fichier {filepath}
- Ne retourne QUE le code Python, rien d'autre
- Ne mets PAS de ```python ou ``` 
- Ne mets PAS d'explications
- Commence directement par le code (import, def, class, etc.)

CODE CORRIGÉ:
"""
            
            # Call Gemini to fix the code
            print(f"  🤖 Appel à Gemini ({DEFAULT_MODEL if not DEV_MODE else 'MOCK'})...")
            try:
                fixed_code_response = call_gemini_with_retry(full_prompt, model_name=DEFAULT_MODEL)
                
                # Debug: Print first 200 chars of response
                print(f"  🔍 Réponse LLM (premiers 200 chars): {fixed_code_response[:200]}")
                
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
                    elif len(parts) == 2:
                        # Sometimes it's just ```\ncode (no closing ```)
                        fixed_code = parts[1].strip()
                
                # Remove any leading explanation text
                # Look for common code starting patterns
                if not any(fixed_code.lstrip().startswith(x) for x in 
                          ['import ', 'from ', 'def ', 'class ', '#', '@', '"""', "'''"]):
                    # Try to find where code actually starts
                    lines = fixed_code.split('\n')
                    for i, line in enumerate(lines):
                        stripped = line.strip()
                        if any(stripped.startswith(x) for x in 
                              ['import ', 'from ', 'def ', 'class ', '#', '@', '"""', "'''"]):
                            fixed_code = '\n'.join(lines[i:])
                            break
                
                # Verify we got actual code (more lenient check)
                fixed_code = fixed_code.strip()
                
                # Accept "pass" as valid minimal code (it compiles)
                if fixed_code == "pass":
                    # This is too minimal, but let's try to compile it
                    print(f"  ⚠️  LLM a retourné seulement 'pass' - probablement une erreur")
                    # We'll let it fail the next check
                
                if not fixed_code or len(fixed_code) < 4:
                    print(f"  ⚠️  Code trop court: {len(fixed_code)} chars")
                    print(f"  📄 Réponse complète: {fixed_code_response[:500]}")
                    raise Exception("Réponse du LLM vide ou trop courte")
                
                # Try to compile to verify it's valid Python
                try:
                    compile(fixed_code, '<string>', 'exec')
                    print(f"  ✅ Syntaxe Python valide ({len(fixed_code)} chars)")
                except SyntaxError as e:
                    print(f"  ❌ Erreur de syntaxe Python: {e}")
                    print(f"  📄 Code reçu: {fixed_code[:200]}")
                    raise Exception(f"Code invalide: {e}")
                
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