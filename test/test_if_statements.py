from util import run_test

def test_basic_if() -> None:
  assert run_test(
    """
      local result = 0
      if true then
        local result = "hello"
        result = "world"
        return result
      end
      return result
    """) == "string | 0"

def test_type_refinement() -> None:
  assert run_test(
    """
      local unknown = (function()
        if true then return 1 else return "a" end
      end)()
      if type(unknown) == "number" then
        return unknown
      end
      return 0
    """) == "number"
