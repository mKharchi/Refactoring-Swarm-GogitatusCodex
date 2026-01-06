from typing import TypedDict, List, Dict, Optional



# This is the primary version of the state used by all agents.

class AgentState(TypedDict):
    """
    Shared state between all agents.
    This is the "memory" that gets passed from agent to agent.
    """
    # Input
    target_dir: str                    # Directory containing code to refactor
    
    # File Management
    python_files: List[str]            # List of .py files found
    current_file: Optional[str]        # File currently being processed
    
    # Auditor Output
    audit_report: Optional[str]        # Full analysis from Auditor
    issues_found: List[Dict]           # Structured list of issues
    pylint_score_before: Optional[float]  # Initial quality score
    
    # Fixer Output
    fixed_code: Optional[Dict[str, str]]  # {filename: fixed_code_content}
    changes_made: List[str]            # Description of changes
    
    # Judge Output
    test_passed: bool                  # Did pytest pass?
    test_output: Optional[str]         # Pytest results
    pylint_score_after: Optional[float]   # Final quality score
    
    # Loop Control
    iteration_count: int               # Current iteration (max 10)
    status: str                        # "running", "success", "failed", "max_iterations"
    error_message: Optional[str]       # If something goes wrong