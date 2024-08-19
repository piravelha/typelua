from util import run_test

def test_multiple_returns() -> None:
  assert run_test(
    """
      return 1, 2, 3
    """) == "(1, 2, 3)"

def test_multiple_returns_of_different_types() -> None:
  assert run_test(
    """
      return 1, true, "hello"
    """) == "(1, true, \"hello\")"
  
def test_multiple_returns_polymorphism() -> None:
  assert run_test(
    """
      function id(x)
        return x
      end
      return id(1), id(true)
    """) == "(number, boolean)"