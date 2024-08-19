from dataclasses import dataclass
from models import *
from type_models import *
from typing import Optional, TypeAlias
from type_helpers import *

global_ctx: Context = Context({})

@dataclass
class UnifyError:
  location: Location
  message: str

UnifyResult: TypeAlias = UnifyError | tuple[Substitution, MonoType]

def set_path(prefix: Expr, value: MonoType, ctx: Context) -> UnifyError | None:
  def get_base(expr: Expr) -> tuple['MonoType | UnifyError', list[MonoType]]:
    if isinstance(expr, Var):
      res = ctx.mapping[expr.name]
      if isinstance(res, ForallType):
        res_t = res.body
      else: assert False
      assert not isinstance(res, ForallType)
      return res_t, []
    elif isinstance(expr, IndexExpr):
      base, path = get_base(expr.obj)
      if isinstance(base, UnifyError): return base, []
      ind = infer(expr.index, ctx)
      if isinstance(ind, UnifyError): return ind, []
      ind_s, ind_t = ind
      return base, path + [ind_t]
    assert False
  if isinstance(prefix, IndexExpr):
    base, paths = get_base(prefix)
    if isinstance(base, UnifyError): return base
    cur_path = base
    for path in paths[:-1]:
      assert isinstance(cur_path, TableType)
      for k, v in cur_path.fields:
        if not isinstance(unify(path, k), str):
          cur_path = v
          break
    assert isinstance(cur_path, TableType)
    new: list[tuple[MonoType, MonoType]] = []
    found = False
    for tup in cur_path.fields:
      k, v = tup
      if not isinstance(unify(paths[-1], k), str):
        subs = unify(value, v)
        if isinstance(subs, str): return UnifyError(prefix.location, subs)
        new.append((k, subs.apply_mono(value)))
        found = True
        continue
      new.append((k, v))
    if not found:
      cur_path.fields.append((paths[-1], value))  
    else:
      cur_path.fields = new
  return None


def infer(node: BaseNode, ctx: Context) -> UnifyResult:
  global global_ctx
  if isinstance(node, Var):
    if node.name in ctx.mapping:
      val = instantiate(ctx.mapping[node.name])
      return Substitution({node.name: val}), val
    if node.name in global_ctx.mapping:
      val = instantiate(global_ctx.mapping[node.name])
      return Substitution({node.name: val}), val
    return UnifyError(node.location, f"Unbound identifier: '{node.name}'")
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
        if not isinstance(k, Number): assert False
        res = infer(v, ctx)
        if isinstance(res, UnifyError): return res
        va_s, va = res
        assert isinstance(va, TableType)
        s = va_s.apply_subst(s)
        types.append((NumberType, [t[1] for t in va.fields][0]))
        continue
      k_res = infer(k, ctx)
      if isinstance(k_res, UnifyError): return k_res
      k_subst, k_type = k_res
      v_res = infer(v, ctx)
      if isinstance(v_res, UnifyError): return v_res
      v_subst, v_type = v_res
      s = k_subst.apply_subst(s)
      s = v_subst.apply_subst(s)
      types.append((k_type, broaden(v_type)))
    return s, TableType(types)
  elif isinstance(node, IndexExpr):
    res = infer(node.obj, ctx)
    if isinstance(res, UnifyError): return res
    obj_s, obj_t = res
    res = infer(node.index, ctx)
    if isinstance(res, UnifyError): return res
    index_s, index_t = res
    beta = new_type_var()
    replace_s = unify(TableType([(index_t, beta)]), obj_t)
    if isinstance(replace_s, str): return UnifyError(node.location, replace_s)
    return replace_s.apply_subst(index_s.apply_subst(obj_s)), replace_s.apply_subst(index_s.apply_subst(obj_s)).apply_mono(beta)
  elif isinstance(node, Vararg):
    if not ctx.mapping.get("..."):
      return UnifyError(node.location, f"Cannot use vararg (...) outside of a vararg-function")
    val = instantiate(ctx.mapping["..."])
    return Substitution({"...": val}), val
  elif isinstance(node, UnaryExpr):
    res = infer(node.value, ctx)
    if isinstance(res, UnifyError): return res
    value_s, value_t = res
    value_t = flatten_tuple(value_t)
    if node.op == "-":
      num_s = unify(value_t, NumberType)
      if isinstance(num_s, str): return UnifyError(node.location, num_s)
      return num_s.apply_subst(value_s), NumberType
    elif node.op == "#":
      # TODO: add union types DONE
      tbl_s = unify(value_t, UnionType(TableType([]), StringType))
      if isinstance(tbl_s, str):
        return UnifyError(node.location, tbl_s)
      return tbl_s.apply_subst(value_s), NumberType
    elif node.op == "not":
      bool_s = unify(value_t, BooleanType)
      if isinstance(bool_s, str): return UnifyError(node.location, bool_s)
      return bool_s.apply_subst(value_s), BooleanType
    assert False
  elif isinstance(node, BinaryExpr):
    res = infer(node.left, ctx)
    if isinstance(res, UnifyError): return res
    left_s, left_t = res
    left_t = flatten_tuple(left_t)
    res = infer(node.right, ctx)
    if isinstance(res, UnifyError): return res
    right_s, right_t = res
    right_t = flatten_tuple(right_t)
    if node.op in ["+", "-", "*", "/", "%", "^"]:
      num_left_s = unify(left_t, NumberType)
      if isinstance(num_left_s, str): return UnifyError(node.location, num_left_s)
      num_right_s = unify(right_t, NumberType)
      if isinstance(num_right_s, str): return UnifyError(node.location, num_right_s)
      return num_left_s.apply_subst(num_right_s.apply_subst(left_s.apply_subst(right_s))), NumberType
    elif node.op in ["<", ">", "<=", ">="]:
      num_left_s = unify(left_t, NumberType)
      if isinstance(num_left_s, str): return UnifyError(node.location, num_left_s)
      num_right_s = unify(right_t, NumberType)
      if isinstance(num_right_s, str): return UnifyError(node.location, num_right_s)
      return num_left_s.apply_subst(num_right_s.apply_subst(left_s.apply_subst(right_s))), BooleanType
    elif node.op == "..":
      str_left_s = unify(left_t, StringType)
      if isinstance(str_left_s, str): return UnifyError(node.location, str_left_s)
      str_right_s = unify(right_t, StringType)
      if isinstance(str_right_s, str): return UnifyError(node.location, str_right_s)
      return str_left_s.apply_subst(str_right_s.apply_subst(left_s.apply_subst(right_s))), StringType
    elif node.op in ["==", "~="]:
      s = Substitution({})
      eq1_s = unify(left_t, right_t)
      if not isinstance(eq1_s, str):
        s = eq1_s.apply_subst(s)
      eq2_s = unify(left_t, right_t)
      if not isinstance(eq2_s, str):
        s = eq2_s.apply_subst(s)
      return left_s.apply_subst(right_s.apply_subst(s)), BooleanType
    elif node.op in ["and", "or"]:
      bool_left_s = unify(left_t, BooleanType)
      if isinstance(bool_left_s, str): return UnifyError(node.location, bool_left_s)
      bool_right_s = unify(right_t, BooleanType)
      if isinstance(bool_right_s, str): return UnifyError(node.location, bool_right_s)
      return bool_left_s.apply_subst(bool_right_s.apply_subst(left_s.apply_subst(right_s))), BooleanType
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
    if node.annotation.ret_type is not None and node.name is not None:
      ctx.mapping[node.name] = TypeConstructor("function", [param_tuple, node.annotation.ret_type, NilType], None)
    res = infer(node.body, ctx)
    if isinstance(res, UnifyError): return res
    body_s, body_t = res
    params = body_s.apply_mono(param_tuple)
    if node.annotation.ret_type is not None:
      ret_anno_s = unify(body_t, node.annotation.ret_type)
      if isinstance(ret_anno_s, str): return UnifyError(node.location, ret_anno_s)
      body_t = ret_anno_s.apply_mono(body_t)
    return body_s, TypeConstructor("function", [params, body_t, var], is_vararg)
  elif isinstance(node, FuncCall):
    params1: list[MonoType] = []
    args_s = Substitution({})
    for arg in node.args:
      res = infer(arg, ctx)
      if isinstance(res, UnifyError): return res
      arg_s, arg_t = res
      args_s = arg_s.apply_subst(args_s)
      if isinstance(arg_t, TypeConstructor) and arg_t.name == "tuple":
        params1.extend([broaden(a) for a in arg_t.args])
      else:
        params1.append(broaden(arg_t))
    beta = new_type_var()
    res = infer(node.func, ctx)
    if isinstance(res, UnifyError): return res
    node_func_s, node_func_t = res
    varargs: MonoType | None = None
    # TODO find a better way to do this
    if isinstance(node_func_t, TypeVariable):
      func_type = TypeConstructor("function", [TypeConstructor("tuple", [broaden(p) for p in params1], None), beta, NilType], None)
      subs = unify(func_type, node_func_t)
      if isinstance(subs, str): return UnifyError(node.location, subs)
      return subs, beta
    assert isinstance(node_func_t, TypeConstructor)
    if node_func_t.value == True:
      assert isinstance(node_func_t.args[0], TypeConstructor)
      for param1 in params1[len(node_func_t.args[0].args):]:
        if varargs is None:
          varargs = broaden(param1)
        subs = unify(param1, varargs)
        if isinstance(subs, str): return UnifyError(node.location, subs)
        varargs = broaden(subs.apply_mono(varargs))
      params1 = params1[:len(node_func_t.args[0].args)]
    func_type = TypeConstructor("function", [TypeConstructor("tuple", params1, None), beta, NilType], None)
    func_s = unify(func_type, node_func_t)
    if isinstance(func_s, str): return UnifyError(node.location, func_s)
    assert isinstance(node_func_t, TypeConstructor)
    replace_s = unify(node_func_t.args[0], TypeConstructor("tuple", params1, None)) 
    if isinstance(replace_s, str): return UnifyError(node.location, replace_s)
    if varargs is not None and node_func_t.args[2] != NilType:
      assert isinstance(node_func_t.args[2], TypeVariable)
      replace_s = Substitution({node_func_t.args[2].name: varargs}).apply_subst(replace_s)
    if isinstance(replace_s, str): return UnifyError(node.location, replace_s)
    # TODO: Stop reyling on applying substitutions multiple times
    final_subs = replace_s.apply_subst(func_s.apply_subst(node_func_s.apply_subst(args_s)))
    return final_subs, final_subs.apply_mono(beta)
  elif isinstance(node, VarDecl):
    exprs: list[MonoType] = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, ctx)
      if isinstance(res, UnifyError): return res
      expr_s, expr_t = res
      if isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        exprs.extend(expr_t.args)
      else:
        exprs.append(expr_t)
      s = expr_s.apply_subst(s)
    for i, name in enumerate(node.names):
      ctx.mapping[name] = ForallType(name, exprs[i])
    return s, NilType
  elif isinstance(node, VarAssign):
    exprs = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, ctx)
      if isinstance(res, UnifyError): return res
      expr_s, expr_t = res
      if isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        exprs.extend(expr_t.args)
      else:
        exprs.append(expr_t)
      s = expr_s.apply_subst(s)
    for i, prefix in enumerate(node.names):
      if not isinstance(prefix, Var):
        err = set_path(prefix, exprs[i], ctx)
        if err:
          return err
        continue
      if ctx.mapping.get(prefix.name):
        existing = instantiate(ctx.mapping[prefix.name])
        subs = unify(exprs[i], broaden(existing))
        if isinstance(subs, str): return UnifyError(node.location, subs)
        ctx.mapping[prefix.name] = subs.apply_mono(exprs[i])
      else:
        ctx.mapping[prefix.name] = exprs[i]
        global_ctx.mapping[prefix.name] = exprs[i]
    return s, NilType
  elif isinstance(node, ReturnStmt):
    exprs = []
    s = Substitution({})
    for expr in node.exprs:
      res = infer(expr, Context(ctx.mapping.copy()))
      if isinstance(res, UnifyError): return res
      expr_s, expr_t = res
      # TODO: find a better way to do this
      args = []
      while isinstance(expr_t, TypeConstructor) and expr_t.name == "tuple":
        args = expr_t.args
        expr_t = expr_t.args[0]
      if args:
        exprs.extend(args)
      else:
        if isinstance(expr, Vararg):
          assert isinstance(expr_t, TableType)
          exprs.extend([t[1] for t in expr_t.fields])
        else:
          exprs.append(expr_t)
      s = expr_s.apply_subst_unsafe(s)
    return s, TypeConstructor("tuple", exprs, None)
  elif isinstance(node, IfStmt):
    res = infer(node.cond, ctx)
    if isinstance(res, UnifyError): return res
    cond_s, cond_t = res
    bool_cond_s = unify(cond_t, BooleanType)
    if isinstance(bool_cond_s, str): return UnifyError(node.location, bool_cond_s)
    res = infer(node.body, ctx)
    if isinstance(res, UnifyError): return res
    body_s, body_t = res
    if node.else_stmt:
      res = infer(node.else_stmt, ctx)
      if isinstance(res, UnifyError): return res
      else_s, else_t = res
      body_s = else_s.apply_subst(body_s)
      subs = unify(else_t, broaden(body_t))
      if isinstance(subs, str): return UnifyError(node.location, subs)
      body_t = subs.apply_mono(broaden(else_t))
    return body_s.apply_subst(cond_s), cond_s.apply_mono(body_t)
  elif isinstance(node, Chunk):
    ctx = Context(ctx.mapping.copy())
    ret: MonoType | None = None
    s = Substitution({})
    for stmt in node.stmts:
      res = infer(stmt, ctx)
      if isinstance(res, UnifyError): return res
      stmt_s, stmt_t = res
      if isinstance(stmt_t, TypeConstructor) and stmt_t.name == "tuple" and not isinstance(stmt, FuncCall):
        if ret is None:
          ret = stmt_t
        ret_s = unify(stmt_t, broaden(ret))
        if isinstance(ret_s, str): return UnifyError(node.location, ret_s)
        ret = ret_s.apply_mono(broaden(ret))
        s = ret_s.apply_subst(s)
      s = stmt_s.apply_subst(s)
    if node.last:
      res = infer(node.last, ctx)
      if isinstance(res, UnifyError): return res
      stmt_s, stmt_t = res
      if not ret:
        ret = stmt_t
      ret_s = unify(stmt_t, broaden(ret))
      if isinstance(ret_s, str): return UnifyError(node.location, ret_s)
      ret = ret_s.apply_mono(broaden(ret))
      s = ret_s.apply_subst(s)
      s = stmt_s.apply_subst(s)
    elif ret:
      ret_s = unify(TypeConstructor("tuple", [], None), ret)
      if isinstance(ret_s, str): return UnifyError(node.location, ret_s)
      ret = ret_s.apply_mono(ret)
    if ret is None:
      ret = TypeConstructor("tuple", [], None)
    return s, ret
  assert False, f"Not implemented: {node}"

