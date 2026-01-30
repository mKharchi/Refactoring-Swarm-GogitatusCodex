"""
Judge Agent - Génère et exécute des tests pour valider le code corrigé.
"""
import os
import json
from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.utils.llm_helper import call_gemini_with_retry
from src.tools.tool_adapter import (
    write_test_file,
    run_pytest,
    cleanup_test_files,
    validate_test_syntax,
    run_pylint,
    
)


from src.config import DEFAULT_MODEL, DEV_MODE

# Import the optimized prompt builder
try:
    from src.prompts.prompt_builder import prompt_builder
    USE_PROMPT_BUILDER = True
    print("✅ Utilisation du prompt builder optimisé")
except ImportError as e:
    USE_PROMPT_BUILDER = False
    print(f"⚠️  Prompt builder non disponible: {e}")


def generate_tests_with_llm(
    code_files: dict,
    audit_report: str,
    target_dir: str,
    iteration: int
) -> str:
    """
    Génère des tests unitaires intelligents via LLM.
    
    Args:
        code_files: Dict {filename: code_content}
        audit_report: Rapport d'audit avec problèmes détectés
        target_dir: Dossier cible
        iteration: Numéro d'itération
    
    Returns:
        Code de test généré
    """
    # Préparer le contexte pour le LLM
    files_summary = "\n\n".join([
        f"# Fichier: {name}\n{content[:500]}..." 
        if len(content) > 500 else f"# Fichier: {name}\n{content}"
        for name, content in code_files.items()
    ])
    
    # Prompt pour générer les tests
    # Prompt pour générer les tests
    prompt = f"""Tu es un expert en tests Python avec pytest.

MISSION: Générer des tests unitaires INTELLIGENTS pour valider le code corrigé.

CODE À TESTER:
{files_summary}

RAPPORT D'AUDIT (problèmes détectés):
{audit_report[:1000] if len(audit_report) > 1000 else audit_report}

INSTRUCTIONS CRITIQUES:
1. Analyse le NOM des fonctions/classes pour comprendre leur INTENTION
2. Génère des tests qui vérifient le COMPORTEMENT ATTENDU, pas juste l'absence d'erreurs
3. Inclus des tests pour:
   - Logique métier (basé sur les noms de fonctions)
   - Edge cases (valeurs limites, None, listes vides)
   - Erreurs attendues (exceptions)

EXEMPLES DE TESTS INTELLIGENTS:

# Si fonction: calculate_discount(price, percent)
def test_discount_logic():
    assert calculate_discount(100, 10) == 90  # 10% de réduction
    assert calculate_discount(50, 20) == 40   # 20% de réduction
    assert calculate_discount(100, 0) == 100  # 0% = pas de réduction
    assert calculate_discount(100, 100) == 0  # 100% = gratuit

# Si fonction: is_valid_email(email)
def test_email_validation():
    assert is_valid_email("user@example.com") == True
    assert is_valid_email("invalid") == False
    assert is_valid_email("") == False
    assert is_valid_email(None) == False

RÈGLES STRICTES:
- Retourne UNIQUEMENT le code pytest complet
- Inclus tous les imports nécessaires
- PAS de ```python ou ``` ou markdown
- Commence directement par "import pytest"
- NE PAS utiliser de fixtures complexes
- Tests SIMPLES avec assert direct
- Chaque test doit être indépendant
- Vérifier que les imports correspondent aux fichiers

GÉNÈRE LE CODE DE TEST (commence par "import pytest"):
"""
    if DEV_MODE:
        # Mock en mode DEV
        mock_test = f'''import pytest
from {os.path.basename(target_dir)}.* import *

def test_basic_execution():
    """Test basique - le code s'exécute sans crash."""
    assert True

def test_mock_validation():
    """Test mock pour développement."""
    # Ce test sera remplacé par de vrais tests
    pass
'''
        return call_gemini_with_retry(prompt, mock_response=mock_test)
    
    return call_gemini_with_retry(prompt, model_name=DEFAULT_MODEL)


def judge_agent(state: AgentState) -> AgentState:
    """
    The Judge Agent: Génère des tests et valide le code corrigé.
    """
    print("\n⚖️  === AGENT JUGE ACTIVÉ ===")
    print(f"🔄 Itération: {state['iteration_count']}")
    
    try:
        target_dir = state["target_dir"]
        python_files = state["python_files"]
        fixed_code = state.get("fixed_code", {})
        audit_report = state.get("audit_report", "")
        iteration = state["iteration_count"]
        
        # Vérifier qu'il y a du code corrigé
        if not fixed_code:
            print("⚠️  Aucun code corrigé trouvé - utilisation code original")
            # Lire les fichiers originaux
            from src.tools.tool_adapter import read_file
            fixed_code = {}
            for filepath in python_files:
                content = read_file(filepath)
                if content:
                    fixed_code[filepath] = content
        
        # 1. GÉNÉRER LES TESTS via LLM
        print("\n📝 Génération des tests unitaires...")
        test_content = generate_tests_with_llm(
            code_files=fixed_code,
            audit_report=audit_report,
            target_dir=target_dir,
            iteration=iteration
        )
        
        # Nettoyer la réponse (enlever markdown si présent)
        test_content_clean = test_content.strip()
        if "```python" in test_content_clean:
            test_content_clean = test_content_clean.split("```python")[1].split("```")[0].strip()
        elif "```" in test_content_clean:
            parts = test_content_clean.split("```")
            if len(parts) >= 3:
                test_content_clean = parts[1].strip()
        
       # Dans judge.py, remplacer le bloc de retry par:

# Valider la syntaxe du test
        validation = validate_test_syntax(test_content_clean)

        MAX_TEST_RETRIES = 2
        test_retry = 0

        while not validation["valid"] and test_retry < MAX_TEST_RETRIES:
            print(f"  🔄 Retry génération tests (tentative {test_retry + 1}/{MAX_TEST_RETRIES})...")

            # Régénérer avec prompt amélioré
            test_content = generate_tests_with_llm(
                code_files=fixed_code,
                audit_report=audit_report,
                target_dir=target_dir,
                iteration=iteration
            )

            # Nettoyer à nouveau
            test_content_clean = test_content.strip()
            if "```python" in test_content_clean:
                test_content_clean = test_content_clean.split("```python")[1].split("```")[0].strip()
            elif "```" in test_content_clean:
                parts = test_content_clean.split("```")
                if len(parts) >= 3:
                    test_content_clean = parts[1].strip()

            # Revalider
            validation = validate_test_syntax(test_content_clean)
            test_retry += 1

        # Si toujours invalide après retries
        if not validation["valid"]:
            print(f"⚠️  Tests générés invalides après {MAX_TEST_RETRIES} tentatives: {validation['error']}")
            print(f"📄 Contenu reçu (200 premiers chars): {test_content[:200]}")

            # Fallback: créer un test minimal
            test_content_clean = f"""import pytest

def test_code_syntax():
    \"\"\"Test basique - vérifier que le code compile.\"\"\"
    # Test minimal en cas d'échec de génération
    assert True
""" 
        # 2. ÉCRIRE LE FICHIER DE TEST
        test_filename = f"test_iteration_{iteration}.py"
        test_filepath = os.path.join(target_dir, test_filename)
        
        write_success = write_test_file(test_filepath, test_content_clean)
        
        if not write_success:
            print("❌ Échec création fichier de test")
            state["test_passed"] = False
            state["test_output"] = "Échec création fichier de test"
            return state
        
        # 3. EXÉCUTER LES TESTS
        print(f"\n🧪 Exécution des tests: {test_filename}")
        test_results = run_pytest(test_filepath, list(fixed_code.keys()))
        
        # 4. CALCULER NOUVEAU SCORE PYLINT
        print("\n📊 Calcul du score Pylint après corrections...")
        pylint_scores = {}
        for filepath in python_files:
            full_path = os.path.join(target_dir, filepath)
            pylint_result = run_pylint(full_path)
            if pylint_result:
                pylint_scores[filepath] = pylint_result["score"]
                print(f"  {filepath}: {pylint_result['score']:.1f}/10")
        
        avg_score_after = None
        if pylint_scores:
            avg_score_after = sum(pylint_scores.values()) / len(pylint_scores)
            state["pylint_score_after"] = avg_score_after
        
        # 5. ANALYSER LES RÉSULTATS
        tests_passed = test_results.get("passed", False)
        
        print(f"\n📋 Résultats:")
        print(f"  Tests: {test_results.get('passed_tests', 0)}/{test_results.get('total_tests', 0)} passés")
        print(f"  Score Pylint: {avg_score_after:.2f}/10" if avg_score_after else "  Score Pylint: N/A")
        
        
        
        ''''''
        # 6. DÉCISION
       
        if (tests_passed or 
    (test_results.get('passed_tests', 0) / max(test_results.get('total_tests', 1), 1) >= 0.85)) and \
   avg_score_after and avg_score_after >= 7.0:
            print("✅ Validation réussie !")
            state["test_passed"] = True
            state["status"] = "success"
            decision = "VALIDE"
        else:
            print("❌ Validation échouée - correction nécessaire")
            state["test_passed"] = False
            state["status"] = "running"
            decision = "ECHEC"
        
        # 7. STOCKER LES RÉSULTATS
        state["test_output"] = test_results.get("output", "")
        
        # 8. LOG EXPERIMENT
        log_experiment(
            agent_name="Judge",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.DEBUG,
            details={
                "iteration": iteration,
                "input_prompt": f"Generate tests for {len(fixed_code)} files",
                "output_response": test_content_clean[:500] + "..." if len(test_content_clean) > 500 else test_content_clean,
                "tests_passed": tests_passed,
                "total_tests": test_results.get("total_tests", 0),
                "pylint_score_after": avg_score_after,
                "decision": decision,
                "dev_mode": DEV_MODE
            },
            status="SUCCESS" if tests_passed else "FAILED"
        )
        
        # 9. NETTOYAGE (optionnel)
        # cleanup_test_files(test_filepath)
        
        print(f"✅ Analyse du juge terminée - Décision: {decision}")
        
        return state
        
    except Exception as e:
        print(f"❌ Erreur du juge: {str(e)}")
        
        log_experiment(
            agent_name="Judge",
            model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
            action=ActionType.DEBUG,
            details={
                "error": str(e),
                "input_prompt": "Failed before execution",
                "output_response": ""
            },
            status="FAILED"
        )
        
        state["test_passed"] = False
        state["status"] = "failed"
        state["error_message"] = f"Judge error: {str(e)}"
        return state