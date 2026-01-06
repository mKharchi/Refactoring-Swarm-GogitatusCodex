from src.state import AgentState
from src.prompts import AUDITOR_SYSTEM_PROMPT

def auditor_agent(state: AgentState) -> AgentState:
    """
    Agent Auditeur - Version Placeholder
    Pour l'instant, il ne fait rien sauf afficher un message.
    """
    print("\n🔍 === AGENT AUDITEUR ACTIVÉ ===")
    print(f"📁 Dossier cible: {state['target_dir']}")
    print(f"📄 Fichiers à analyser: {len(state['python_files'])}")
    print(f"📋 Prompt système chargé: {len(AUDITOR_SYSTEM_PROMPT)} caractères")
    print("⏳ [PLACEHOLDER] Analyse non implémentée pour l'instant")
    
    # Simuler qu'on a fait quelque chose
    state["audit_report"] = "[PLACEHOLDER] Rapport d'audit non généré"
    state["iteration_count"] = 1
    
    return state