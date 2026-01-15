import pytest

def test_syntax():
    # This test file itself might check if the other file is importable
    # But since the other file has syntax error, simple import will fail.
    # The Judge likely runs pytest on the folder.
    # If case5_syntax.py is broken, pytest might collect error or fail.
    # This test expects that eventually it becomes importable.
    try:
        import case5_syntax
        assert True
    except SyntaxError:
        pytest.fail("Syntax Error in case5_syntax.py")
    except ImportError:
         pytest.fail("Import Error")
