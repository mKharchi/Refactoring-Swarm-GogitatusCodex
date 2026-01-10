"""
Test script to verify Prompt Engineer's optimization work.
"""
import os

def count_tokens_rough(text: str) -> int:
    """
    Rough token estimate: ~1 token per 4 characters for English/French
    Real tokenizers are more accurate, but this is good enough.
    """
    return len(text) // 4

def load_prompt(filepath: str) -> str:
    """Load a prompt file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return None

print("🔍 PROMPT OPTIMIZATION VERIFICATION")
print("=" * 70)

# Check Auditor prompts
prompts_to_check = [
    ("Auditor System", "src/prompts/system_prompts/auditor_current_prompt.txt"),
    ("Fixer System", "src/prompts/system_prompts/fixer_current_prompt.txt"),
    ("Judge System", "src/prompts/system_prompts/judge_current_prompt.txt"),
]

results = []

for name, filepath in prompts_to_check:
    content = load_prompt(filepath)
    
    if content is None:
        print(f"❌ {name}: File not found - {filepath}")
        results.append((name, None, "MISSING"))
    else:
        tokens = count_tokens_rough(content)
        chars = len(content)
        
        # Determine status
        if tokens <= 450:
            status = "✅ OPTIMIZED"
        elif tokens <= 600:
            status = "⚠️  ACCEPTABLE"
        else:
            status = "❌ TOO LONG"
        
        print(f"{status} {name}")
        print(f"   Path: {filepath}")
        print(f"   Characters: {chars}")
        print(f"   Estimated tokens: ~{tokens}")
        print()
        
        results.append((name, tokens, status))

# Summary
print("=" * 70)
print("📊 SUMMARY")
print("=" * 70)

total_optimized = sum(1 for _, _, status in results if "OPTIMIZED" in status)
total_files = len([r for r in results if r[1] is not None])

print(f"Optimized prompts: {total_optimized}/{total_files}")

if all("OPTIMIZED" in r[2] or "ACCEPTABLE" in r[2] for r in results if r[1] is not None):
    print("\n✅ OPTIMIZATION SUCCESSFUL!")
    print("All prompts meet token requirements.")
else:
    print("\n❌ OPTIMIZATION INCOMPLETE")
    print("Some prompts still need work.")

# Check for new utility files
print("\n" + "=" * 70)
print("🔧 UTILITY FILES CHECK")
print("=" * 70)

utils = [
    "src/prompts/prompt_optimizer.py",
    "src/prompts/prompt_builder.py",
    "src/prompts/prompt_validator.py",
]

for util_file in utils:
    if os.path.exists(util_file):
        size = os.path.getsize(util_file)
        print(f"✅ {util_file} ({size} bytes)")
    else:
        print(f"❌ {util_file} - NOT FOUND")