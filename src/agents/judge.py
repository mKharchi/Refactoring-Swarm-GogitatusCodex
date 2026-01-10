from src.state import AgentState

def judge_agent(state: AgentState) -> AgentState:
    """
    Agent Juge - Version Placeholder
    """
    print("\n⚖️  === AGENT JUGE ACTIVÉ ===")
    print(f"🔄 Itération: {state['iteration_count']}")
    print("⏳ [PLACEHOLDER] Tests non implémentés pour l'instant")
    
    # Pour tester la boucle: échec 2 fois, puis succès
    if state["iteration_count"] < 3:
        print("❌ [SIMULATION] Tests échoués")
        state["test_passed"] = False
        state["iteration_count"] += 1
    else:
        print("✅ [SIMULATION] Tests réussis")
        state["test_passed"] = True
    
    return state