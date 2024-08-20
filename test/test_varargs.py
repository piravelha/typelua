from util import run_test

def test_simple_varargs() -> None:
  assert run_test(
    """
      function vararg(...)
        return ({...})[1]
      end
      local x = vararg(1, 2, 3)
      return x
    """) == "number"
