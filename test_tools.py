"""
Test the enhanced real tools.
"""
from src.tools.tool_adapter import (
    read_file, write_file, list_python_files,
    run_pylint
)

print("🧪 Testing Enhanced Real Tools")
print("=" * 70)

# Test 1: Write file
print("\n[TEST 1] Writing test file...")
success = write_file("test_sample.py", """
def hello(name):
    print(f'Hello {name}')
    
def add(a,b):
    return a+b
""")
print(f"{'✅' if success else '❌'} Write: {success}")

# Test 2: Read file
print("\n[TEST 2] Reading file...")
content = read_file("test_sample.py")
if content:
    print(f"✅ Read: {len(content)} chars")
    print(f"Preview: {content[:50]}...")
else:
    print("❌ Read failed")

# Test 3: List Python files
print("\n[TEST 3] Listing Python files...")
files = list_python_files(".")
print(f"✅ Found {len(files)} Python files")
for f in files[:3]:
    print(f"  - {f}")

# Test 4: Pylint with specific file
print("\n[TEST 4] Running pylint on specific file...")
result = run_pylint("good_code.py")
if result:
    print(f"✅ Pylint: Score {result['score']}/10")
    print(f"   Issues: {result['total_issues']}")
    print(f"   Errors: {len(result['errors'])}")
    print(f"   Warnings: {len(result['warnings'])}")
else:
    print("❌ Pylint failed")

# Test 5: Security test
print("\n[TEST 5] Security test (should fail)...")
content = read_file("../../main.py")
if content is None:
    print("✅ Security: Correctly blocked access outside sandbox")
else:
    print("❌ SECURITY BREACH!")

print("\n" + "=" * 70)
print("✅ All tests complete!")