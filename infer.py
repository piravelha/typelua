from models import *
from type_models import *
from typing import Optional
from type_helpers import *

global_ctx: Context = Context({})

def infer(node: BaseNode, ctx: Context) -> Optional[tuple[Substitution, MonoType]]:
  global global_ctx
  if isinstance(node, Var):
    if node.name in ctx.mapping:
      val = instantiate(ctx.mapping[node.name])
      return Substitution({node.name: val}), val
    if node.name in global_ctx.mapping:
      val = instantiate(global_ctx.mapping[node.name])
      return Substitution({node.name: val}), val
    assert False, f"Unknown identifier: {node.name}"
  elif isinstance(node, Nil):
    return Substitution({}), TypeConstructor("nil", [], None)
  elif isinstance(node, Number):
    return Substitution({}), TypeConstructor("number", [], node.value)
  elif isinstance(node, String):
    return Substitution({}), TypeConstructor("string", [], node.value)
  elif isinstance(node, Boolean):
    return Substitution({}), TypeConstructor("boolean", [], node.value)
  elif isinstance(node, Table):
    s = Substitution({})
    types: list[tuple[MonoType, MonoType]] = []
    for k, v in node.fields:
      if isinstance(v, Vararg):
        if not isinstance(k, Number): return None
        res = infer(v, ctx)
        if res is None: return res
        va_s, va = res
        assert isinstance(va, TableType)
        s = va_s.apply_subst(s)
        types.append((NumberType, [t[1] for t in va.fields][0]))
        continue
      k_res = infer(k, ctx)
      if k_res is None: return k_res
      k_subst, k_type = k_res
      v_res = infer(v, ctx)
      if v_res is None: return v_res
      v_subst, v_type = v_res
      s = k_subst.apply_subst(s)
      s = v_subst.apply_subst(s)
      types.append((k_type, v_type))
    return s, TableType(types)
  elif isinstance(node, IndexExpr):
    res = infer(node.obj, ctx)
    if res is None: return res
    obj_s, obj_t = res
    res = infer(node.index, ctx)
    if res is None: return res
    index_s, index_t = res
    beta = new_type_var()
    replace_s = unify(TableType([(index_t, beta)]), obj_t)
    if replace_s is None: return replace_s
    return replace_s.apply_subst(index_s.apply_subst(obj_s)), replace_s.apply_subst(index_s.apply_subst(obj_s)).apply_mono(beta)
  elif isinstance(node, Vararg):
    if not ctx.mapping.get("..."):
      return None
    val = instantiate(ctx.mapping["..."])
    return Substitution({"...": val}), val
  elif isinstance(node, UnaryExpr):
    res = infer(node.value, ctx)
    if not res: return res
    value_s, value_t = res
    if node.op == "-":
      num_s = unify(value_t, NumberType)
      if num_s is None: return num_s
      return num_s.apply_subst(value_s), NumberType
    elif node.op == "#":
      tbl_s = unify(value_t, TableType([]))
      if tbl_s is None: return tbl_s
      return tbl_s.apply_subst(value_s), NumberType
    elif node.op == "not":
      bool_s = unify(value_t, BooleanType)
      if bool_s is None: return bool_s
      return bool_s.apply_subst(value_s), BooleanType
    assert False
  elif isinstance(node, BinaryExpr):
    res = infer(node.left, ctx)
    if res is None: return res
    left_s, left_t = res
    res = infer(node.right, ctx)
    if res is None: return res
    right_s, right_t = res
    if node.op in ["+", "-", "*", "/", "%", "^"]:
      num_left_s = unify(left_t, NumberType)
      if num_left_s is None: return num_left_s
      num_right_s = unify(right_t, NumberType)
      if num_right_s is None: return num_right_s
      return num_left_s.apply_subst(num_right_s.apply_subst(left_s.apply_subst(right_s))), NumberType
    elif node.op in ["<", ">", "<=", ">="]:
      num_left_s = unify(left_t, NumberType)
      if num_left_s is None: return num_left_s
      num_right_s = unify(right_t, NumberType)
      if num_right_s is None: return num_right_s
      return num_left_s.apply_subst(num_right_s.apply_subst(left_s.apply_subst(right_s))), BooleanType
    elif node.op == "..":
      str_left_s = unify(left_t, StringType)
      if str_left_s is None: return str_left_s
      str_right_s = unify(right_t, StringType)
      if str_right_s is None: return str_right_s
      return str_left_s.apply_subst(str_right_s.apply_subst(left_s.apply_subst(right_s))), StringType
    elif node.op in ["==", "~="]:
      s = Substitution({})
      eq1_s = unify(left_t, right_t)
      if eq1_s is not None:
        s = eq1_s.apply_subst(s)
      eq2_s = unify(left_t, right_t)
      if eq2_s is not None:
        s = eq2_s.apply_subst(s)
      return s, BooleanType
    assert False
  elif isinstance(node, FuncExpr):
    param_types: list[MonoType] = []
    ctx = Context(ctx.mapping.copy())
    for param in node.params:
      new_var = new_type_var()
      ctx.mapping[param] = new_var
      param_types.append(new_var)
    is_vararg = False
    var: MonoType = NilType
    if node.is_vararg:
      is_vararg = True
      var = new_type_var()
      ctx.mapping["..."] = TableType([(NumberType, var)])
    param_tuple = TypeConstructor("tuple", param_types, None)
    res = infer(node.body, ctx)
    if res is None: return res
    body_s, body_t = res
    params = body_s.apply_mono(param_tuple)
    return body_s, TypeConstructor("function", [params, body_t, var], is_vararg)
  elif isinstance(node, FuncCall):
    params1: list[MonoType] = []
    args_s = Substitution({})
    for arg in node.args:
      res = infer(arg, ctx)
      if res is None: return res
      arg_s, arg_t = res
      args_s = arg_s.apply_subst(args_s)
      if isinstance(arg_t, TypeConstructor) and arg_t.name == "tuple":
        params1.extend(arg_t.args)
      else:
        params1.append(arg_t)
    beta = new_type_var()
    res = infer(node.func, ctx)
    if res is None: return res
    node_func_s, node_func_t = res
    varargs: MonoType | None = None
    assert isinstance(node_func_t, TypeConstructor)
    if node_func_t.value == True:
      assert isinstance(node_func_t.args[0], TypeConstructor)
      for param1 in params1[len(node_func_t.args[0].args):]:
        if varargs is None:
          varargs = broaden(param1)
        subs = unify(param1, varargs)
        if subs is None: return subs
        varargs = broaden(subs.apply_mono(varargs))
      params1 = params1[:len(node_func_t.args[0].args)]
    func_type = TypeConstructor("function", [TypeConstructor("tuple", params1, None), beta, NilType], None)
    func_s = unify(func_type, node_func_t)
    if func_s is None: return func_s
    assert isinstance(node_func_t, TypeConstructor)
    replace_s = unify(node_func_t.args[0], TypeConstructor("tuple", params1, None)) 
    if replace_s is None: return replace_s
    if varargs is not None and node_func_t.args[2] != NilType:
      assert isinstance(node_func_t.args[2], TypeVariable)
      replace_s = Substitution({node_func_t.args[2].name: varargs}).apply_subst(replace_s)
    if replace_s is None: return replace_s
    return replace_s.apply_subst(func_s.apply_subst(node_func_s.apply_subst(args_s))), replace_s.apply_subst(func_s.apply_subst(node_func_s)).apply_mono(beta)
  elif isinstance(node, VarDecl):
    exprs: list[MonoType] = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, ctx)
      if res is None: return res
      expr_s, expr_t = res
      if isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        exprs.extend(expr_t.args)
      else:
        exprs.append(expr_t)
      s = expr_s.apply_subst(s)
    for i, name in enumerate(node.names):
      ctx.mapping[name] = exprs[i]
    return s, NilType
  elif isinstance(node, VarAssign):
    exprs = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, ctx)
      if res is None: return res
      expr_s, expr_t = res
      if isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        exprs.extend(expr_t.args)
      else:
        exprs.append(expr_t)
      s = expr_s.apply_subst(s)
    for i, name in enumerate(node.names):
      global_ctx.mapping[name] = exprs[i]
    return s, NilType
  elif isinstance(node, ReturnStmt):
    exprs = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, ctx)
      if res is None: return res
      expr_s, expr_t = res
      if isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        exprs.extend(expr_t.args)
      else:
        if isinstance(expr, Vararg):
          assert isinstance(expr_t, TableType)
          exprs.extend([t[1] for t in expr_t.fields])
        else:
          exprs.append(expr_t)
      s = expr_s.apply_subst(s)
    return s, TypeConstructor("tuple", exprs, None)
  elif isinstance(node, Chunk):
    ret: MonoType | None = None
    s = Substitution({})
    for stmt in node.stmts:
      res = infer(stmt, ctx)
      if res is None: return res
      stmt_s, stmt_t = res
      if isinstance(stmt_t, TypeConstructor) and stmt_t.name == "tuple" and not isinstance(stmt, FuncCall):
        if ret is None:
          ret = stmt_t
        ret_s = unify(stmt_t, ret)
        if ret_s is None: return ret_s
        ret = ret_s.apply_mono(ret)
        s = ret_s.apply_subst(s)
      s = stmt_s.apply_subst(s)
    if node.last:
      res = infer(node.last, ctx)
      if res is None: return res
      stmt_s, stmt_t = res
      if not ret:
        ret = stmt_t
      ret_s = unify(stmt_t, ret)
      if ret_s is None: return ret_s
      ret = ret_s.apply_mono(ret)
      s = ret_s.apply_subst(s)
      s = stmt_s.apply_subst(s)
    if ret is None:
      ret = TypeConstructor("tuple", [NilType], None)
    return s, ret
  assert False, f"Not implemented: {node}"

