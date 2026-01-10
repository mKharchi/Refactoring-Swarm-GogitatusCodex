"""Test the prompt builder functionality - CORRECTED VERSION."""

try:
    # Import the instance, not a function
    from src.prompts.prompt_builder import prompt_builder
    
    test_code = """
def hello():
    print("Hello World")
"""
    
    print("✅ Testing Prompt Builder (Corrected)...")
    print("=" * 70)
    
    # Call the correct method with correct parameters
    system_prompt, user_prompt = prompt_builder.construire_prompt_auditeur(
        code_source=test_code,
        nom_fichier="test.py",
        score_pylint=5.0
    )
    
    # Combine for total length
    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    
    print(f"✅ Prompt Builder Works!")
    print(f"\nSystem prompt length: {len(system_prompt)} chars (~{len(system_prompt)//4} tokens)")
    print(f"User prompt length: {len(user_prompt)} chars (~{len(user_prompt)//4} tokens)")
    print(f"Total length: {len(full_prompt)} chars (~{len(full_prompt)//4} tokens)")
    
    # Show previews
    print(f"\n--- System Prompt Preview (first 200 chars) ---")
    print(system_prompt[:200])
    print("...")
    
    print(f"\n--- User Prompt Preview ---")
    print(user_prompt[:300])
    print("...")
    
    # Check if optimized
    total_tokens = len(full_prompt) // 4
    if total_tokens < 800:
        print(f"\n✅ Prompt is well optimized! (~{total_tokens} tokens)")
    else:
        print(f"\n⚠️  Prompt might be long (~{total_tokens} tokens)")
    
    # Test other methods too
    print("\n" + "=" * 70)
    print("Testing Fixer prompt builder...")
    
    test_problemes = [
        {
            "fichier": "test.py",
            "ligne": 1,
            "type": "bug",
            "severite": "critique",
            "description": "Test bug",
            "suggestion": "Fix it"
        }
    ]
    
    system_fixer, user_fixer = prompt_builder.construire_prompt_correcteur(
        code_source=test_code,
        problemes=test_problemes,
        nom_fichier="test.py"
    )
    
    print(f"✅ Fixer prompt: {len(system_fixer) + len(user_fixer)} chars")
    
    # Test Judge
    print("\nTesting Judge prompt builder...")
    
    system_judge, user_judge = prompt_builder.construire_prompt_testeur(
        resultats_tests="2 passed, 1 failed",
        scores_pylint={"test.py": 5.0},
        iteration=1
    )
    
    print(f"✅ Judge prompt: {len(system_judge) + len(user_judge)} chars")
    
    print("\n" + "=" * 70)
    print("✅ ALL PROMPT BUILDERS WORK CORRECTLY!")
        
except ImportError as e:
    print(f"❌ Cannot import prompt_builder: {e}")
    import traceback
    traceback.print_exc()
except AttributeError as e:
    print(f"❌ Method not found: {e}")
    print("\nAvailable methods:")
    from src.prompts.prompt_builder import prompt_builder
    print([m for m in dir(prompt_builder) if not m.startswith('_')])
except Exception as e:
    print(f"❌ Error testing prompt builder: {e}")
    import traceback
    traceback.print_exc()