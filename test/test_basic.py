from util import run_test

def test_basic_number() -> None:
  assert run_test(
    """
      return 10
    """) == "10"

def test_basic_string() -> None:
  assert run_test(
    """
      return "Hello, World!"
    """) == "\"Hello, World!\""

def test_basic_boolean() -> None:
  assert run_test(
    """
      return true
    """) == "true"

def test_basic_nil() -> None:
  assert run_test(
    """
      return nil
    """) == "nil"

def test_basic_empty() -> None:
  assert run_test(
    """
      return
    """) == "()"
