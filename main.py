from lark import Tree
from typing import Any
from parser import parser, ToAST
from models import *
from type_models import *
from infer import *

import sys

file_path = None
args = sys.argv[1:]
is_debug = False

while args:
  if args[0] == "--debug":
    is_debug = True
    _, *args = args
  else:
    file_path = args[0]
    _, *args = args

assert file_path is not None
fp = file_path

with open(file_path) as f:
  input = f.read()

def run(code: str) -> None:
  tree: Tree[Any] = parser.parse(code)
  ast = ToAST(fp).transform(tree)
  res = infer(ast, Context({}))
  if isinstance(res, UnifyError):
    print(f"{res.location}: {res.message}")
    exit(1)
  if is_debug:
    _, typ = res
    print(typ)
  else:
    print(f"No issues found in {file_path}")

if __name__ == "__main__":
  run(input)