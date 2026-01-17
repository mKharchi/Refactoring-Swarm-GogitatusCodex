from src.state import AgentState
from src.utils.logger import log_experiment, ActionType
from src.config import DEFAULT_MODEL, DEV_MODE

def judge_agent(state: AgentState) -> AgentState:
    """
    Agent Juge - Version Placeholder
    """
    print("\n⚖️  === AGENT JUGE ACTIVÉ ===")
    print(f"🔄 Itération: {state['iteration_count']}")
    print("⏳ [PLACEHOLDER] Tests non implémentés pour l'instant")
    
    # Pour tester la boucle: échec 2 fois, puis succès
    status_msg = ""
    if state["iteration_count"] < 3:
        status_msg = "❌ [SIMULATION] Tests échoués"
        print(status_msg)
        state["test_passed"] = False
        state["iteration_count"] += 1
    else:
        status_msg = "✅ [SIMULATION] Tests réussis"
        print(status_msg)
        state["test_passed"] = True
    
    # Log the experiment
    log_experiment(
        agent_name="Judge",
        model_used=DEFAULT_MODEL if not DEV_MODE else "MOCK-DEV",
        action=ActionType.DEBUG,
        details={
            "iteration": state["iteration_count"],
            "input_prompt": "Run tests on fixed code", # Placeholder prompt
            "output_response": status_msg,
            "test_passed": state["test_passed"],
            "changes_verified": state.get("changes_made", [])
        },
        status="SUCCESS" if state["test_passed"] else "FAILURE"
    )
    
    return state