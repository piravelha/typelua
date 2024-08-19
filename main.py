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

tree: Tree[Any] = parser.parse(input)
ast = ToAST().transform(tree)
res = infer(ast, Context({}))
print(res[1] if not isinstance(res, UnifyError) else f"{res.location}: {res.message}")

