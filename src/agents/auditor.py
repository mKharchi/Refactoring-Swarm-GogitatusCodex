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


def classify_repository_type(json_data: dict, pylint_results: list) -> list:
    """
    Classifie le type de dépôt basé sur l'analyse des problèmes.
    
    Amélioration: Évite les classifications incohérentes comme ["CLEAN", "NAMING"]
    et priorise correctement les problèmes.
    
    Args:
        json_data: Données JSON de l'audit contenant les problèmes
        pylint_results: Résultats pylint pour calculer le score moyen
        
    Returns:
        Type de dépôt: Liste contenant un ou plusieurs types (SYNTAX, LOGIC, NAMING, DOCUMENTATION, CLEAN)
    """
    problemes = json_data.get("problemes", [])
    
    # Calculer le score pylint moyen
    avg_score = 0
    if pylint_results:
        avg_score = sum(r["score"] for r in pylint_results) / len(pylint_results)
    
    # Compter les types de problèmes
    type_counts = {
        "bug": 0,
        "pep8": 0,
        "documentation": 0,
        "naming": 0
    }
    
    severity_counts = {
        "critique": 0,
        "majeur": 0,
        "mineur": 0
    }
    
    for prob in problemes:
        prob_type = prob.get("type", "").lower()
        severity = prob.get("severite", "").lower()
        
        if prob_type in type_counts:
            type_counts[prob_type] += 1
        
        if severity in severity_counts:
            severity_counts[severity] += 1
    
    total_problems = sum(type_counts.values())
    
    # ============ CAS SPÉCIAL: AUCUN PROBLÈME ============
    if total_problems == 0:
        return ["CLEAN"]
    
    # ============ DÉTECTION DES TYPES ============
    detected_types = []
    
    # 1. SYNTAX: Erreurs syntaxiques bloquantes (PRIORITÉ 1)
    syntax_keywords = ["syntax", "import", "indentation", "undefined", "name error", "importerror"]
    syntax_bugs = sum(
        1 for prob in problemes 
        if prob.get("type") == "bug" 
        and any(kw in prob.get("description", "").lower() for kw in syntax_keywords)
    )
    has_critical_bugs = severity_counts["critique"] > 0 and type_counts["bug"] > 0
    
    if syntax_bugs > 0 or (has_critical_bugs and avg_score < 3.0):
        detected_types.append("SYNTAX")
        return detected_types  # SYNTAX masque tous les autres types
    
    # 2. LOGIC: Bugs fonctionnels (PRIORITÉ 2)
    # Ne trigger que s'il y a des bugs ET pas d'autres problèmes dominants
    if type_counts["bug"] > 0 and avg_score >= 4.0:
        # Vérifier que ce ne sont pas juste des problèmes de documentation
        if type_counts["documentation"] < total_problems * 0.7:  # Docs ≠ majorité
            detected_types.append("LOGIC")
    
    # 3. DOCUMENTATION: Code fonctionne mais pas documenté (PRIORITÉ 3)
    # Doit avoir AU MOINS des problèmes de documentation ET peu/pas de bugs
    if type_counts["documentation"] > 0 and type_counts["bug"] == 0:
        # Si documentation est le seul ou majoritaire problème
        if type_counts["documentation"] >= total_problems * 0.5:
            detected_types.append("DOCUMENTATION")
    
    # 4. NAMING: Code fonctionne mais mal nommé (PRIORITÉ 4)
    # Doit avoir des problèmes de nommage ET pas de bugs/docs manquantes
    if type_counts["naming"] > 0:
        # Ne ajouter NAMING que si:
        # - Pas de bugs
        # - Ou très peu de docs manquantes
        if type_counts["bug"] == 0 and type_counts["documentation"] < total_problems * 0.5:
            if type_counts["naming"] >= total_problems * 0.3:
                detected_types.append("NAMING")
    
    # ============ FALLBACK: MIXED ============
    if not detected_types:
        # S'il y a des problèmes mais aucun type ne s'applique nettement
        detected_types.append("MIXED")
    
    # ============ DÉDUPLICATIONS ET COHÉRENCE ============
    # Supprimer les contradictions
    if "CLEAN" in detected_types and len(detected_types) > 1:
        detected_types.remove("CLEAN")
    
    # Si SYNTAX ou LOGIC détecté, supprimer les types cosmétiques
    if "SYNTAX" in detected_types or "LOGIC" in detected_types:
        if "DOCUMENTATION" in detected_types and type_counts["documentation"] < 3:
            detected_types.remove("DOCUMENTATION")
    
    # Log debugging
    print(f"  📊 Problèmes comptés: {type_counts}")
    print(f"  📊 Sévérités: {severity_counts}")
    print(f"  📊 Score pylint moyen: {avg_score:.2f}")
    print(f"  📊 Types détectés: {detected_types}")
    
    return detected_types if detected_types else ["MIXED"]


def auditor_agent(state: AgentState) -> AgentState:
    """The Auditor Agent: Analyzes code and creates a refactoring plan."""
    print("\n🔍 === AGENT AUDITEUR ACTIVÉ (v1.1.0 - Avec classification dépôt) ===")
    
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
            # Fallback to enhanced prompt with repo classification
            print("⚠️  Utilisation du prompt amélioré (fallback)")
            full_prompt = f"""Tu es un expert Python senior en analyse de code.

MISSION: Analyser du code Python et identifier les problèmes de qualité.

TYPES DE PROBLÈMES:
1. BUGS: Division par zéro, variables non définies, erreurs de types, exceptions non gérées
2. PEP8: Nommage incorrect, lignes >79 car, imports désorganisés, espaces manquants
3. DOCUMENTATION: Fonctions sans docstring, format non-Google Style
4. NAMING: Variables à une lettre, noms non descriptifs

FORMAT SORTIE (STRICT):
JSON uniquement, pas de texte, pas de markdown.

{{
  "score_qualite": <0-10>,
  "problemes": [
    {{
      "fichier": "nom.py",
      "ligne": <int>,
      "type": "bug|pep8|documentation|naming",
      "severite": "critique|majeur|mineur",
      "description": "<max 80 car>",
      "suggestion": "<max 100 car>"
    }}
  ],
  "resume": "<max 150 car>"
}}

RÈGLES ANTI-HALLUCINATION:
- Ne jamais inventer de problèmes inexistants
- Vérifier chaque numéro de ligne
- Être factuel et précis
- Si aucun problème: {{"score_qualite": 10, "problemes": [], "resume": "Code conforme"}}

CRITÈRES SCORE:
10: Parfait | 8-9: Mineurs | 6-7: PEP8/doc | 4-5: Bugs mineurs | 0-3: Bugs critiques

PRIORITÉ: bugs > documentation > pep8 > naming

CODE À ANALYSER:
{all_code}

Score Pylint actuel: {avg_score:.2f}/10 si disponible

Retourne UNIQUEMENT le JSON."""
        
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
            
            # ===== NOUVEAUTÉ v1.1.0: Classification du dépôt =====
            print("\n🏷️  Classification du type de dépôt...")
            repo_type = classify_repository_type(json_data, pylint_results)
            json_data["repo_type"] = repo_type
            
            print(f"📊 Type de dépôt détecté: {repo_type}")
            
            # Ajouter des statistiques de classification dans les logs
            type_stats = {}
            for prob in json_data.get("problemes", []):
                prob_type = prob.get("type", "unknown")
                type_stats[prob_type] = type_stats.get(prob_type, 0) + 1
            
            print(f"📈 Distribution des problèmes: {type_stats}")
            # ===================================================
            
            # Re-serialize with repo_type
            audit_report_clean = json.dumps(json_data, ensure_ascii=False, indent=2)
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
                "resume": "Erreur de parsing - rapport incomplet",
                "repo_type": "MIXED"  # Default safe value
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
                "json_valid": True,
                "repo_type": json_data.get("repo_type", "UNKNOWN"),  # Log the classification
                "version": "1.1.0"
            },
            status="SUCCESS"
        )
        
        # Update state
        state["audit_report"] = audit_report
        state["iteration_count"] = 1
        state["repo_type"] = json_data.get("repo_type", "MIXED")  # Store in state
        
        print("✅ Analyse de l'auditeur terminée")
        if avg_score:
            print(f"📊 Score Pylint moyen: {avg_score:.2f}/10")
        print(f"🏷️  Type de dépôt: {state['repo_type']}")
        
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
                "output_response": "",
                "version": "1.1.0"
            },
            status="FAILED"
        )
        
        state["status"] = "failed"
        state["error_message"] = f"Auditor error: {str(e)}"
        return state