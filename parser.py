from lark import Lark

parser = Lark.open("grammar.lark")

print(parser.parse(
  """
  local x = 5
  print(({ y = x }).y + #({1, 2}))
  """
).pretty())
