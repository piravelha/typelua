from lark import Lark, Transformer, Token, Tree
from typing import Any, cast
from models import *
from type_models import *

import sys

parser = Lark.open("grammar.lark")

def get_loc(file_path: str, node: Token | Tree[Any]) -> Location:
  if isinstance(node, Token):
    assert node.line is not None
    assert node.column is not None
    return Location(file_path, node.line, node.column)
  if isinstance(node, Tree):
    if node.meta.empty:
      return get_loc(file_path, node.children[0])
    return Location(file_path, node.meta.line, node.meta.column)
  assert False, f"get_loc: Argument must be either a Token or a Tree, got {node}"

class ToAST(Transformer[Tree[Any], BaseNode]):
  def __init__(self, file_path: str):
    self.file_path = file_path
  def chunk(self, args: list[Stmt | ReturnStmt]) -> BaseNode:
    stmts: list[Stmt] = []
    ret: ReturnStmt | None = None
    loc: Location | None = None
    for arg in args:
      if isinstance(arg, ReturnStmt):
        ret = arg
      elif arg:
        stmts.append(arg)
        loc = loc or arg.location
    return Chunk(loc or Location(self.file_path, 0, 0), stmts, ret)
  def func_expr(self, args: tuple[Tree[Any] | None, FuncAnnotation, Chunk]) -> BaseNode:
    params, annotation, body = args
    param_strs: list[str] = []
    is_vararg: bool = False
    loc: Location | None = None
    if not params: pass
    elif len(params.children) == 2:
      is_vararg = params.children[1] is not None
      ps = params.children[0]
      for param in ps.children:
        assert isinstance(param, Token)
        if not loc:
          loc = get_loc(self.file_path, param)
        assert isinstance(param.value, str)
        param_strs.append(param.value)
    else:
      is_vararg = params.children[0] is not None
    if not loc:
      loc = Location(self.file_path, 0, 0)
    return FuncExpr(loc, param_strs, is_vararg, body, None, annotation)
  
  def if_stmt(self, args: tuple[Expr, Chunk, Tree[Any], Tree[Any] | None]) -> BaseNode:
    cond, body, elseif_stmts, else_stmt = args
    elifs: list[ElseifStmt] = []
    for elseif in elseif_stmts.children:
      assert isinstance(elseif, Tree)
      elseif_cond, elseif_body = elseif.children
      assert is_expr(elseif_cond)
      assert isinstance(elseif_body, Chunk) 
      elifs.append(ElseifStmt(elseif_cond.location, elseif_cond, elseif_body))
    else_chunk: Chunk | None = None
    if else_stmt:
      chunk = else_stmt.children[0]
      assert isinstance(chunk, Chunk)
      else_chunk = chunk
    return IfStmt(cond.location, cond, body, elifs, else_chunk)
  def return_stmt(self, args: tuple[Tree[Any]]) -> BaseNode:
    exprs = args[0]
    expr_exprs: list[Expr] = []
    loc: Location | None = None
    exprs = exprs or Tree("exprs", [])
    for expr in exprs.children:
      assert is_expr(expr)
      expr_exprs.append(expr)
      if not loc:
        loc = expr.location
    if not loc:
      loc = Location(self.file_path, 0, 0)
    return ReturnStmt(loc, expr_exprs)
  def func_assign(self, args: tuple[Token, Tree[Any] | None, FuncAnnotation, Chunk]) -> BaseNode:
    name, params, annotation, body = args
    param_strs: list[str] = []
    is_vararg: bool = False
    loc: Location | None = None
    if not params: pass
    elif len(params.children) == 2:
      is_vararg = params.children[1] is not None
      ps = params.children[0]
      for param in ps.children:
        assert isinstance(param, Token)
        if not loc:
          loc = get_loc(self.file_path, param)
        assert isinstance(param.value, str)
        param_strs.append(param.value)
    else:
      is_vararg = params.children[0] is not None
    if not loc:
      loc = Location(self.file_path, 0, 0)
    return VarAssign(get_loc(self.file_path, name), [Var(get_loc(self.file_path, name), name.value)], [FuncExpr(loc, param_strs, is_vararg, body, name.value, annotation)])
  def func_decl(self, args: tuple[Token, Tree[Any] | None, FuncAnnotation, Chunk]) -> BaseNode:
  
    name, params, annotation, body = args
    param_strs: list[str] = []
    is_vararg: bool = False
    loc: Location | None = None
    if not params: pass
    elif len(params.children) == 2:
      is_vararg = params.children[1] is not None
      ps = params.children[0]
      for param in ps.children:
        assert isinstance(param, Token)
        if not loc:
          loc = get_loc(self.file_path, param)
        assert isinstance(param.value, str)
        param_strs.append(param.value)
    else:
      is_vararg = params.children[0] is not None
    if not loc:
      loc = Location(self.file_path, 0, 0)
    return VarDecl(get_loc(self.file_path, name), [name.value], [FuncExpr(loc, param_strs, is_vararg, body, name.value, annotation)], None)
  def var_assign(self, args: tuple[Tree[Any], Tree[Any]]) -> BaseNode:
    names, exprs = args
    name_strs: list[Expr] = []
    expr_exprs: list[Expr] = []
    for name in names.children:
      if isinstance(name, str):
        name = Var(Location(self.file_path, 0, 0), name)
      assert is_expr(name)
      name_strs.append(name)
    for expr in exprs.children:
      assert is_expr(expr)
      expr_exprs.append(expr)
    return VarAssign(expr_exprs[0].location, name_strs, expr_exprs)
  def var_decl(self, args: tuple[Optional[VarAnnotation], Tree[Any], Tree[Any]]) -> BaseNode:
    annotation, names, exprs = args
    name_strs: list[str] = []
    expr_exprs: list[Expr] = []
    for name in names.children:
      assert isinstance(name, Token)
      assert isinstance(name.value, str)
      name_strs.append(name.value)
    for expr in exprs.children:
      assert is_expr(expr)
      expr_exprs.append(expr)
    return VarDecl(expr_exprs[0].location, name_strs, expr_exprs, annotation)
  def func_annotations(self, args: list[Tree[Any]]) -> FuncAnnotation:
    ret = None
    for arg in args:
      if arg.data == "return_type_annotation":
        ret = cast(MonoType, arg.children[0])
    return FuncAnnotation(Location(self.file_path, 0, 0), ret)
  def var_type_annotation(self, args: tuple[MonoType]) -> VarAnnotation:
    return VarAnnotation(Location(self.file_path, 0, 0), args[0])
  def reveal_annotation(self, args: tuple[Expr]) -> RevealAnnotation:
    return RevealAnnotation(args[0].location, args[0])
  def index_expr(self, args: tuple[Expr, Expr]) -> BaseNode:
    obj, index = args
    return IndexExpr(obj.location, obj, index)
  def prop_expr(self, args: tuple[Expr, Token]) -> BaseNode:
    obj, prop = args
    return IndexExpr(obj.location, obj, String(obj.location, str(prop.value)))
  def func_call(self, args: tuple[Expr, Tree[Any]]) -> BaseNode:
    func, arguments = args
    expr_args: list[Expr] = []
    for arg in arguments.children:
      assert is_expr(arg)
      expr_args.append(arg)
    return FuncCall(func.location, func, expr_args)
  def table(self, args: list[Tree[Any]]) -> BaseNode:
    fields: list[tuple[Expr, Expr]] = []
    i: float = 1.0
    location: Location | None = None
    for field in args:
      loc: Location | None = None
      if field.data == "table_field":
        expr = field.children[0]
        assert is_expr(expr)
        loc = expr.location
        fields.append((Number(expr.location, i), expr))
      elif field.data == "obj_field":
        prop, expr = field.children
        assert isinstance(prop, Token)
        assert is_expr(expr)
        fields.append((String(get_loc(self.file_path, prop), prop.value),  expr))
        loc = get_loc(self.file_path, prop)
      elif field.data == "dict_field":
        key, expr = field.children
        assert is_expr(key)
        assert is_expr(expr)
        loc = key.location
        fields.append((key, expr))
      else: assert False, f"Unknown field type: {field.data}"
      if not location:
        location = loc
      i += 1.0
    if not location:
      location = Location(self.file_path, 0, 0)
    return Table(location, fields)
  def binary_expr(self, args: tuple[Expr, Token, Expr]) -> BaseNode:
    left, op, right = args
    return BinaryExpr(left.location, left, op.value, right)
  log_expr = binary_expr
  eq_expr = binary_expr
  rel_expr = binary_expr
  add_expr = binary_expr
  mul_expr = binary_expr
  pow_expr = binary_expr
  def unary_expr(self, args: tuple[Token, Expr]) -> BaseNode:
    op, expr = args
    return UnaryExpr(get_loc(self.file_path, op), op.value, expr)
  def var(self, args: tuple[Token]) -> BaseNode:
    return Var(get_loc(self.file_path, args[0]), args[0].value)
  def union_type(self, args: tuple[MonoType, MonoType]) -> MonoType:
    return UnionType(args[0], args[1])
  def type_var(self, args: tuple[Token]) -> TypeVariable:
    return TypeVariable(args[0].value)
  def tuple_type(self, args: list[MonoType]) -> MonoType:
    return TypeConstructor("tuple", args, None, [])
  def PRIMITIVE_TYPE(self, token: Token) -> MonoType:
    if token.value == "number":
      return NumberType
    elif token.value == "string":
      return StringType
    elif token.value == "boolean":
      return BooleanType
    elif token.value == "nil":
      return NilType
    assert False
  def ELLIPSIS(self, token: Token) -> BaseNode:
    return Vararg(get_loc(self.file_path, token))
  def NIL(self, token: Token) -> BaseNode:
    return Nil(get_loc(self.file_path, token))
  def BOOLEAN(self, token: Token) -> BaseNode:
    return Boolean(get_loc(self.file_path, token), token.value == "true")
  def STRING(self, token: Token) -> BaseNode:
    return String(get_loc(self.file_path, token), token.value[1:-1])
  def NUMBER(self, token: Token) -> BaseNode:
    return Number(get_loc(self.file_path, token), float(token.value))


