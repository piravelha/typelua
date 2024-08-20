from lark import Tree
from typing import Any
from parser import parser, ToAST
from models import *
from type_models import *
from infer import *

import sys

file_path = sys.argv[1]
with open(file_path) as f:
  input = f.read()

def run(code: str) -> None:
  tree: Tree[Any] = parser.parse(code)
  ast = ToAST().transform(tree)
  res = infer(ast, Context({}))
  if isinstance(res, UnifyError):
    print(f"{res.location}: {res.message}")
  print(f"No issues found in {file_path}")

if __name__ == "__main__":
  run(input)