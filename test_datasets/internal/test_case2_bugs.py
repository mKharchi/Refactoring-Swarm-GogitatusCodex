import pytest
from case2_bugs import divide_numbers, get_element

def test_divide_numbers():
    assert divide_numbers(10, 2) == 5
    # The refined code should probably handle this or raise a specific exception
    # For now, let's assume valid inputs work
    
def test_divide_by_zero_handling():
    # If the agent fixes it, it might raise ValueError or return None
    # This test expects the agent to make it robust.
    # We'll assert that it raises an Exception (as it does now), 
    # BUT the goal is that the agent might change it to handle it gacefully?
    # Actually, usually refactoring keeps behavior but fixes crashes. 
    # Let's just test happy path for now, and see if the Judge logic handles the crash.
    with pytest.raises(ZeroDivisionError):
        divide_numbers(1, 0)

def test_get_element():
    assert get_element([1, 2, 3], 1) == 2
