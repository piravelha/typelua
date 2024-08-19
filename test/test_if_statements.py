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
    """) == "\"world\" | 0"