from lark import Tree
from typing import Any
from parser import parser, ToAST
from models import *
from type_models import *
from infer import *
from stdlib import ctx

import sys

file_path = sys.argv[1]
with open(file_path) as f:
  input = f.read()

def run(code: str) -> None:
  tree: Tree[Any] = parser.parse(code)
  ast = ToAST().transform(tree)
  res = infer(ast, ctx)
  print(res[1] if not isinstance(res, UnifyError) else f"{res.location}: {res.message}")

if __name__ == "__main__":
  run(input)