from lark import Tree
from typing import Any
from parser import parser, ToAST
from models import *
from type_models import *
from infer import infer

input = """
function changePerson(p)
  return {
    name2 = p.name .. "!",
    age2 = p.age + 1,
  }
end

local obj = {
  person = {
    name = "Ian",
    age = 15,
  }
}

return changePerson(obj.person)
""" # '{name2: string, age2: number}'

tree: Tree[Any] = parser.parse(input)
ast = ToAST().transform(tree)
res = infer(ast, Context({}))
print(res[1] if res else None)

