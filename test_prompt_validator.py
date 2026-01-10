# test_validator.py
"""Test the prompt validator."""

try:
    from src.prompts.prompt_validator import prompt_validator
    
    # Test with valid JSON
    valid_json = '''
{
  "score_qualite": 8,
  "problemes": [
    {
      "fichier": "test.py",
      "ligne": 1,
      "type": "pep8",
      "severite": "mineur",
      "description": "Test problem",
      "suggestion": "Test fix"
    }
  ],
  "resume": "Test summary"
}
'''
    
    result = prompt_validator.valider_reponse_auditeur(valid_json)
    
    if result:
        print("✅ Validator works correctly!")
        print("Valid JSON was accepted")
    else:
        print("❌ Validator rejected valid JSON")
    
    # Test with invalid JSON
    invalid_json = "Not valid JSON at all"
    result = prompt_validator.valider_reponse_auditeur(invalid_json)
    
    if not result:
        print("✅ Validator correctly rejects invalid JSON")
    else:
        print("❌ Validator accepted invalid JSON")
        
except ImportError as e:
    print(f"❌ Cannot import validator: {e}")
except Exception as e:
    print(f"❌ Error testing validator: {e}")