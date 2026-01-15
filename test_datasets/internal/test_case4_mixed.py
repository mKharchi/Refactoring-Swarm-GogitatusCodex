import pytest
from case4_mixed import process_data

def test_process_data():
    data = {1: 'a', 2: 'b'}
    result = process_data(data)
    assert '1' in result
    assert '2' in result
