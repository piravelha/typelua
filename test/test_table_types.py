from util import run_test

def test_array_type() -> None:
  assert run_test(
    """
      function get_arr()
        return {"a", "b", "c"}
      end
      return get_arr()
    """) == "string[]"

def test_array_tuple_type() -> None:
  assert run_test(
    """
      return {1, "hello"}
    """) == "{[1]: 1, [2]: \"hello\"}"

def test_dict_type() -> None:
  assert run_test(
    """
      local dict = {}
      dict["hello" .. "!"] = 1 + 1
      return dict
    """) == "{[string]: number}"
  
def test_object_type() -> None:
  assert run_test(
    """
      local person = { extra = true }
      person.name = "Ian"
      person.age = 15
      return person
    """) == "{extra: true, name: \"Ian\", age: 15}"
  
def test_state_type() -> None:
  assert run_test(
    """
      local state = { [true] = "On", [false] = "Off" }
      return state, state[true], state[false]
    """) == "({[true]: \"On\", [false]: \"Off\"}, \"On\", \"Off\")"