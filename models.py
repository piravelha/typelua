from dataclasses import dataclass
from typing import TypeAlias, Union, Optional, TypeGuard, Any

@dataclass
class Location:
  file: str
  line: int
  column: int
  def __repr__(self) -> str:
    return f"{self.file}:{self.line}:{self.column}"

@dataclass
class BaseNode:
  location: Location

Expr: TypeAlias = Union[
  'Var',
  'Nil',
  'Number',
  'Boolean',
  'String',
  'Table',
  'Vararg',
  'UnaryExpr',
  'BinaryExpr',
  'FuncCall',
  'IndexExpr',
  'FuncExpr',
]

def is_expr(value: Any) -> TypeGuard[Expr]:
  return isinstance(value, BaseNode)
  
Stmt: TypeAlias = Union[
  'VarDecl',
  'VarAssign',
  'IfStmt',
  'FuncCall',
]

@dataclass
class Var(BaseNode):
  name: str

@dataclass
class Number(BaseNode):
  value: float

@dataclass
class Boolean(BaseNode):
  value: bool

@dataclass
class String(BaseNode):
  value: str

@dataclass
class Nil(BaseNode): pass

@dataclass
class Vararg(BaseNode): pass

@dataclass
class UnaryExpr(BaseNode):
  op: str
  value: Expr

@dataclass
class BinaryExpr(BaseNode):
  left: Expr
  op: str
  right: Expr

@dataclass
class Table(BaseNode):
  fields: list[tuple[Expr, Expr]]

@dataclass
class FuncCall(BaseNode):
  func: Expr
  args: list[Expr]

@dataclass
class IndexExpr(BaseNode):
  obj: Expr
  index: Expr

@dataclass
class VarDecl(BaseNode):
  names: list[str]
  exprs: list[Expr]

@dataclass
class VarAssign(BaseNode):
  names: list[str]
  exprs: list[Expr]

@dataclass
class FuncExpr(BaseNode):
  params: list[str]
  is_vararg: bool
  body: 'Chunk'

@dataclass
class ReturnStmt(BaseNode):
  exprs: list[Expr]

@dataclass
class ElseifStmt(BaseNode):
  cond: Expr
  body: 'Chunk'

@dataclass
class IfStmt(BaseNode):
  cond: Expr
  body: 'Chunk'
  elseif_stmts: list[ElseifStmt]
  else_stmt: Optional['Chunk']

@dataclass
class Chunk(BaseNode):
  stmts: list[Stmt]
  last: Optional[ReturnStmt]

