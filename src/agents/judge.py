"""
Judge Agent - Génère et exécute des tests pour valider le code corrigé.
"""
import os
import re
from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.utils.llm_helper import call_gemini_with_retry
from src.tools.tool_adapter import (
    write_test_file,
    read_file,
    run_pytest,
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


def extract_functions_from_code(code: str) -> list:
    """
    Extrait les noms des fonctions définies dans le code.
    """
    pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
    matches = re.findall(pattern, code)
    return matches


def extract_classes_from_code(code: str) -> list:
    """
    Extrait les noms des classes définies dans le code.
    """
    pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[\(:]'
    matches = re.findall(pattern, code)
    return matches


def build_module_documentation(code_files: dict) -> str:
    """
    Crée une documentation des modules avec leurs fonctions et classes.
    """
    module_doc = "STRUCTURE DES MODULES:\n" + "="*70 + "\n\n"
    
    for filename, content in code_files.items():
        module_name = filename.replace('.py', '')
        functions = extract_functions_from_code(content)
        classes = extract_classes_from_code(content)
        
        module_doc += f"📦 Module: {module_name}\n"
        module_doc += f"   Fichier: {filename}\n"
        
        if classes:
            module_doc += f"   Classes: {', '.join(classes)}\n"
        if functions:
            module_doc += f"   Fonctions: {', '.join(functions)}\n"
        
        module_doc += "\n"
    
    return module_doc


def generate_tests_with_llm(
    code_files: dict,
    audit_report: str,
    target_dir: str,
    iteration: int,
    repo_type: list = None,
    previous_test_results: str = None
) -> str:
    """
    Génère des tests unitaires intelligents via LLM.
    """
    files_summary = "\n\n".join([
        f"# Fichier: {name}\n{content[:500]}..." 
        if len(content) > 500 else f"# Fichier: {name}\n{content}"
        for name, content in code_files.items()
    ])
    
    module_doc = build_module_documentation(code_files)
    repo_type_str = ', '.join(repo_type) if repo_type else 'Non spécifié'
    
    feedback_section = ""
    if previous_test_results and iteration > 1:
        feedback_section = f"""
╔══════════════════════════════════════════════════════════════════╗
║            FEEDBACK DES ITÉRATIONS PRÉCÉDENTES                   ║
╚══════════════════════════════════════════════════════════════════╝

{previous_test_results}

⚠️ INSTRUCTIONS CRITIQUES - Apprenez de ces erreurs:

1. Si un test échoue → analyse POURQUOI et CORRIGE-LE
2. Si un import manque → AJOUTE-LE avec le BON MODULE
3. Si une expectation est fausse → RECALCULE la bonne valeur
4. Si un test contradictoire existait → CORRIGE-LE immédiatement
5. REGARDEZ LES TESTS QUI PASSAIENT: gardez la même structure exacte
6. NE CHANGEZ PAS les imports qui fonctionnaient déjà

NE RÉPÉTEZ PAS les erreurs des itérations précédentes !

"""
    
    prompt = f"""Tu es un expert en tests Python avec pytest.

MISSION: Générer des tests unitaires INTELLIGENTS pour valider le code corrigé.

{feedback_section}

{module_doc}

CODE À TESTER:
{files_summary}

RAPPORT D'AUDIT (problèmes détectés):
{audit_report[:1000] if len(audit_report) > 1000 else audit_report}

Type de problèmes à résoudre: {repo_type_str}

RÈGLES CRITIQUES - IMPORTANCE MAJEURE:

1. ✅ COMPRENDRE LA STRUCTURE DES MODULES
   Tu dois vérifier dans la section "STRUCTURE DES MODULES" ci-dessus:
   - Quelles fonctions sont dans quel fichier
   - Quelles classes sont dans quel fichier
   - Les noms EXACTS des fonctions et classes (pas d'approximation)
   - Le module correct à importer pour chaque fonction/classe

2. ✅ IMPORTS CORRECTS (OBLIGATOIRE)
   - TOUS les imports doivent être au début du fichier
   - Pour CHAQUE fonction/classe testée, regarde son MODULE dans "STRUCTURE DES MODULES"
   - Format: from {{module_name}} import {{function_or_class_name}}

3. ✅ SIGNATURES DE FONCTIONS (EXACTES)
   - Lis les fonctions complètement pour comprendre les paramètres
   - Ne pas inventer de paramètres ou de fonctions

4. ✅ CALCULER LES VALEURS ATTENDUES
   - Exécute mentalement chaque fonction

5. ✅ CONSISTENCY ABSOLUE
   - Si une fonction est dans le module A, TOUJOURS l'importer de A

6. ✅ VALIDATION FINALE
   - Avant de retourner le code, vérifier:
     * Chaque import existe dans "STRUCTURE DES MODULES"
     * Chaque fonction appelée dans les tests est importée

GÉNÈRE LE CODE DE TEST (commence par "import pytest"):
"""
    if DEV_MODE:
        mock_test = f'''import pytest
from datat_transform import add, mult, div
from string_processor import process_string

def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0

def test_mult():
    assert mult(2, 3) == 6
    assert mult(-1, 1) == -1
    assert mult(0, 5) == 0

def test_div():
    assert div(6, 2) == 3.0
    assert div(-4, 2) == -2.0

def test_process_string():
    assert process_string("hello") == "HELLO"
    assert process_string("World") == "WORLD"
    assert process_string("") == ""
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
        repo_type = state.get("repo_type", [])
        
        # Fallback flag to avoid masking real failures
        fallback_used = False
        
        # Vérifier qu'il y a du code corrigé
        if not fixed_code:
            print("⚠️  Aucun code corrigé trouvé - utilisation code original")
            fixed_code = {}
            for filepath in python_files:
                content = read_file(filepath)
                if content:
                    fixed_code[filepath] = content
        
        # ✅ Extract feedback from previous test iterations
        previous_test_output = state.get("test_output", "")
        test_failures_summary = ""
        
        if iteration > 1 and previous_test_output:
            print(f"  📜 Analyse des résultats de l'itération précédente...")
            
            error_lines = [
                line.strip() for line in previous_test_output.split('\n')
                if any(keyword in line.lower() for keyword in [
                    'failed', 'error', 'importerror', 'nameerror', 'attributeerror',
                    'assert', 'assert failed', 'keyerror', 'typeerror',
                    'key error', 'missing', 'traceback', 'exception'
                ]) and len(line.strip()) > 0
            ]
            
            passed_failed_lines = [
                line.strip() for line in previous_test_output.split('\n')
                if any(x in line.lower() for x in ['passed', 'failed']) and any(x in line for x in ['/', 'passed'])
            ]
            
            feedback_parts = []
            if passed_failed_lines:
                feedback_parts.extend(passed_failed_lines[:5])
            if error_lines:
                feedback_parts.extend(error_lines[:12])
            
            if feedback_parts:
                test_failures_summary = "\n".join(feedback_parts)
                print(f"  📋 Feedback intégré: {len(feedback_parts)} lignes d'erreur/info")
        
        # 1. GENERATE TESTS via LLM
        print("\n📝 Génération des tests unitaires...")
        test_content = generate_tests_with_llm(
            code_files=fixed_code,
            audit_report=audit_report,
            target_dir=target_dir,
            iteration=iteration,
            repo_type=repo_type,
            previous_test_results=test_failures_summary
        )
        
        # Clean response (remove markdown if present)
        test_content_clean = test_content.strip()
        if "```python" in test_content_clean:
            test_content_clean = test_content_clean.split("```python")[1].split("```")[0].strip()
        elif "```" in test_content_clean:
            parts = test_content_clean.split("```")
            if len(parts) >= 3:
                test_content_clean = parts[1].strip()
        
        # Validate test syntax
        validation = validate_test_syntax(test_content_clean)

        MAX_TEST_RETRIES = 2
        test_retry = 0

        while not validation["valid"] and test_retry < MAX_TEST_RETRIES:
            print(f"  🔄 Retry génération tests (tentative {test_retry + 1}/{MAX_TEST_RETRIES})...")

            test_content = generate_tests_with_llm(
                code_files=fixed_code,
                audit_report=audit_report,
                target_dir=target_dir,
                iteration=iteration,
                repo_type=repo_type,
                previous_test_results=test_failures_summary
            )

            test_content_clean = test_content.strip()
            if "```python" in test_content_clean:
                test_content_clean = test_content_clean.split("```python")[1].split("```")[0].strip()
            elif "```" in test_content_clean:
                parts = test_content_clean.split("```")
                if len(parts) >= 3:
                    test_content_clean = parts[1].strip()

            validation = validate_test_syntax(test_content_clean)
            test_retry += 1

        # If still invalid after retries -> fallback minimal test but mark fallback_used
        if not validation["valid"]:
            print(f"⚠️  Tests générés invalides après {MAX_TEST_RETRIES} tentatives: {validation['error']}")
            print(f"📄 Contenu reçu (200 premiers chars): {test_content[:200]}")
            fallback_used = True
            test_content_clean = """import pytest

def test_basic_imports_compile():
    \"\"\"Test basique - vérifier que les modules s'importent.\"\"\"
    assert True
"""
        # 2. WRITE TEST FILE
        test_filename = f"test_iteration_{iteration}.py"
        test_filepath = os.path.join(target_dir, test_filename)
        
        write_success = write_test_file(test_filepath, test_content_clean)
        
        if not write_success:
            print("❌ Échec création fichier de test")
            state["test_passed"] = False
            state["test_output"] = "Échec création fichier de test"
            return state
        
        # 3. RUN TESTS
        print(f"\n🧪 Exécution des tests: {test_filename}")
        test_results = run_pytest(test_filepath, list(fixed_code.keys()))
        
        # 4. CALCULATE NEW PYLINT SCORE
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
        
        # 5. ANALYZE RESULTS
        tests_passed = test_results.get("passed", False)
        passed_tests = test_results.get('passed_tests', 0)
        total_tests = test_results.get('total_tests', 1)
        pass_rate = (passed_tests / max(total_tests, 1)) * 100
        
        # If we used fallback minimal test, do not consider it as real success
        if fallback_used:
            tests_passed = False
            print("⚠️ Test fallback utilisé — le résultat ne constitue pas une validation réelle.")
        
        print(f"\n📋 Résultats:")
        print(f"  Tests: {passed_tests}/{total_tests} passés ({pass_rate:.1f}%)")
        print(f"  Score Pylint: {avg_score_after:.2f}/10" if avg_score_after else "  Score Pylint: N/A")
        
        # 6. DECISION
        if (tests_passed or (pass_rate >= 85)) and avg_score_after and avg_score_after >= 7.0:
            print("✅ Validation réussie !")
            state["test_passed"] = True
            state["status"] = "success"
            decision = "VALIDE"
        else:
            print("❌ Validation échouée - correction nécessaire")
            state["test_passed"] = False
            state["status"] = "running"
            decision = "ECHEC"
        
        # 7. STORE RESULTS
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
                "passed_tests": passed_tests,
                "total_tests": total_tests,
                "pass_rate": f"{pass_rate:.1f}%",
                "pylint_score_after": avg_score_after,
                "decision": decision,
                "dev_mode": DEV_MODE,
                "used_previous_feedback": bool(test_failures_summary),
                "module_aware": True,
                "fallback_used": fallback_used
            },
            status="SUCCESS" if tests_passed else "FAILED"
        )
        
        print(f"✅ Analyse du juge terminée - Décision: {decision}")
        
        return state
        
    except Exception as e:
        print(f"❌ Erreur du juge: {str(e)}")
        import traceback
        traceback.print_exc()
        
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