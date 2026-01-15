import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add src to path if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

# Force UTF-8 output for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

from src.utils.logger import ActionType

LOG_FILE = Path("logs/experiment_data.json")

def validate_logs():
    print(f"🔍 Validating logs from: {LOG_FILE}")
    
    if not LOG_FILE.exists():
        print("❌ Log file not found!")
        return False

    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON format: {e}")
        return False

    if not isinstance(data, list):
        print("❌ Root element is not a list")
        return False

    required_fields = ["id", "timestamp", "agent", "model", "action", "details", "status"]
    valid_actions = [a.value for a in ActionType]
    
    errors = 0
    warnings = 0
    
    for i, entry in enumerate(data):
        entry_id = entry.get("id", f"Index {i}")
        
        # 1. Check required fields
        missing_fields = [field for field in required_fields if field not in entry]
        if missing_fields:
            print(f"❌ [Entry {entry_id}] Missing fields: {missing_fields}")
            errors += 1
            continue

        # 2. Check ActionType
        if entry["action"] not in valid_actions and entry["action"] != "STARTUP":
             # Allow STARTUP as a legacy or system action if found in existing logs, 
             # but strictly enforce ActionType for agents.
             # Based on previous file view, "STARTUP" was present.
             msg = f"⚠️ [Entry {entry_id}] Unknown action type: '{entry['action']}'"
             print(msg)
             warnings += 1

        # 3. Check Mandatory Details for specific actions
        current_action = entry["action"]
        details = entry["details"]
        
        # Actions requiring prompt/response
        needs_prompt_response = [
            ActionType.ANALYSIS.value,
            ActionType.GENERATION.value,
            ActionType.DEBUG.value,
            ActionType.FIX.value
        ]
        
        if current_action in needs_prompt_response:
            if "input_prompt" not in details:
                print(f"❌ [Entry {entry_id}] Missing 'input_prompt' in details (Required for {current_action})")
                errors += 1
            if "output_response" not in details:
                print(f"❌ [Entry {entry_id}] Missing 'output_response' in details (Required for {current_action})")
                errors += 1
                
    print("\n" + "="*30)
    print(f"Validation Complete.")
    print(f"Entries checked: {len(data)}")
    print(f"Errors: {errors}")
    print(f"Warnings: {warnings}")
    
    if errors == 0:
        print("✅ LOGS ARE VALID")
        return True
    else:
        print("❌ LOGS ARE INVALID")
        return False

if __name__ == "__main__":
    success = validate_logs()
    sys.exit(0 if success else 1)
