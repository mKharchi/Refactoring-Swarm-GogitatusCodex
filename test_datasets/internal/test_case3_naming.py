import pytest
from case3_naming import fn, c

def test_fn():
    assert fn(5) == 10

def test_class_method():
    # If the agent renames the class, this test might break if it tries to import 'c'.
    # This is a good test of the system: does it break external consumers?
    # The requirement said "Ne jamais renommer fonctions publiques" but classes?
    # Actually, "Ne jamais renommer fonctions publiques" is a priority.
    # Naming is Priority 4.
    obj = c()
    assert obj.m() == "hello"
