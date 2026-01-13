import argparse
import sys
import os
from dotenv import load_dotenv
from typing import Literal
from langgraph.graph import StateGraph, END
from pathlib import Path

# Charger les variables d'environnement
load_dotenv()

# Importer après avoir chargé l'environnement
from src.state import AgentState
from src.agents.auditor import auditor_agent
from src.agents.fixer import fixer_agent
from src.agents.judge import judge_agent


def should_continue(state: AgentState) -> Literal["continue", "end"]:
    """
    Fonction de décision : Continuer la boucle ou arrêter ?
    
    Conditions d'arrêt :
    1. Tests réussis (succès !)
    2. Itérations max atteintes (10)
    3. Erreur critique
    """
    # Cas de succès
    if state.get("test_passed", False):
        state["status"] = "success"
        return "end"
    
    # Itérations max atteintes
    if state["iteration_count"] >= 10:
        state["status"] = "max_iterations"
        return "end"
    
    # Erreur critique
    if state.get("status") == "failed":
        return "end"
    
    # Continuer la boucle
    return "continue"


def build_workflow() -> StateGraph:
    """
    Construit le graphe d'exécution des agents.
    
    Flow :
    Auditeur → Correcteur → Juge
                    ↑         ↓
                    └─────────┘ (si échec, reboucle)
    """
    workflow = StateGraph(AgentState)
    
    # Ajouter les nœuds (agents)
    workflow.add_node("auditor", auditor_agent)
    workflow.add_node("fixer", fixer_agent)
    workflow.add_node("judge", judge_agent)
    
    # Définir le flux
    workflow.add_edge("auditor", "fixer")   # Auditeur → Correcteur
    workflow.add_edge("fixer", "judge")     # Correcteur → Juge
    
    # Arête conditionnelle depuis le Juge
    workflow.add_conditional_edges(
        "judge",
        should_continue,
        {
            "continue": "fixer",  # Reboucler vers Correcteur si échec
            "end": END            # Arrêter si succès ou max itérations
        }
    )
    
    # Définir le point d'entrée
    workflow.set_entry_point("auditor")
    
    return workflow


def initialize_state(target_dir: str) -> AgentState:
    """
    Crée l'état initial pour le workflow.
    """
    # Trouver tous les fichiers Python dans le dossier cible
    python_files = []
    for root, dirs, files in os.walk(target_dir):
        for file in files:
            if file.endswith('.py'):
                
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, start=target_dir)                    
                python_files.append(rel_path)
                
    
    return {
        "target_dir": target_dir,
        "python_files": python_files,
        "current_file": None,
        "audit_report": None,
        "issues_found": [],
        "pylint_score_before": None,
        "fixed_code": {},
        "changes_made": [],
        "test_passed": False,
        "test_output": None,
        "pylint_score_after": None,
        "iteration_count": 0,
        "status": "running",
        "error_message": None
    }


def main():
    """
    Point d'entrée du Refactoring Swarm.
    """
    # Parser les arguments de ligne de commande
    parser = argparse.ArgumentParser(
        description="The Refactoring Swarm - Système de Refactoring Autonome"
    )
    parser.add_argument(
        '--target_dir',
        required=True,
        help='Dossier contenant le code Python à refactorer'
    )
    args = parser.parse_args()
    
    # Valider le dossier cible
    if not os.path.exists(args.target_dir):
        print(f"❌ Erreur : Le dossier '{args.target_dir}' n'existe pas !")
        sys.exit(1)
    
    print("🐝 Démarrage du Refactoring Swarm...")
    print(f"📁 Dossier Cible : {args.target_dir}")
    print("=" * 70)
    
    # Initialiser l'état
    initial_state = initialize_state(args.target_dir)
    print(f"📄 Trouvé {len(initial_state['python_files'])} fichier(s) Python")
    
    if len(initial_state['python_files']) == 0:
        print("⚠️  Aucun fichier Python trouvé dans le dossier cible !")
        sys.exit(0)
    
    print("\n🏗️  Construction du workflow...")
    
    # Construire et compiler le workflow
    workflow = build_workflow()
    app = workflow.compile()
    
    print("✅ Workflow construit avec succès !")
    print("\n🚀 Lancement du processus de refactoring...\n")
    
    # Exécuter le workflow
    try:
        final_state = app.invoke(initial_state)
        
        # Afficher les résultats
        print("\n" + "=" * 70)
        print("🏁 Refactoring Terminé !")
        print("=" * 70)
        print(f"📊 Statut Final     : {final_state['status']}")
        print(f"🔄 Itérations       : {final_state['iteration_count']}")
        print(f"✅ Tests Réussis    : {final_state['test_passed']}")
        
        if final_state.get('pylint_score_before') and final_state.get('pylint_score_after'):
            print(f"📈 Score Qualité    : {final_state['pylint_score_before']:.2f} → {final_state['pylint_score_after']:.2f}")
        
        print()
        if final_state['status'] == 'success':
            print("✅ SUCCÈS : Code refactorisé et tous les tests passent !")
        elif final_state['status'] == 'max_iterations':
            print("⚠️  ATTENTION : Nombre max d'itérations atteint sans succès complet")
        else:
            print(f"❌ ÉCHEC : {final_state.get('error_message', 'Erreur inconnue')}")
            
    except Exception as e:
        print(f"\n❌ ERREUR CRITIQUE : {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()