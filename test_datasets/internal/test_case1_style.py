import pytest
from case1_style import calculate_sum, check_parity

def test_calculate_sum():
    assert calculate_sum(1, 2) == 3
    assert calculate_sum(-1, 1) == 0

def test_check_parity():
    assert check_parity(2) is True
    assert check_parity(3) is False
