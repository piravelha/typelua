from dataclasses import dataclass
from models import *
from type_models import *
from typing import Optional, TypeAlias
from type_helpers import *
from stdlib import ctx

global_ctx: Context = ctx

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
      assert not isinstance(res_t, ForallType)
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
        subs = unify(value, broaden(v))
        if isinstance(subs, str): return UnifyError(prefix.location, subs)
        new.append((k, subs.apply_mono(broaden(value))))
        found = True
        continue
      new.append((k, v))
    if not found:
      cur_path.fields.append((paths[-1], value))  
    else:
      cur_path.fields = new
  return None


def infer_type_check_predicate(node: IfStmt, ctx: Context) -> Optional[UnifyError]:
  cond = node.cond
  if isinstance(cond, BinaryExpr):
    left, right = cond.left, cond.right
    if cond.op == "==":
      if isinstance(left, FuncCall):
        func, args = left.func, left.args
        if isinstance(func, Var) and func.name == "type" and "type" not in ctx.mapping:
          assert len(args) == 1
          arg = args[0]
          assert isinstance(arg, Var)
          if isinstance(right, String):
            contents = right.value
            res = infer(arg, ctx)
            if isinstance(res, UnifyError): return res
            _, arg_t = res
            type: MonoType | None = None
            if contents == "number":
              type = NumberType
            elif contents == "string":
              type = StringType
            elif contents == "boolean":
              type = BooleanType
            elif contents == "nil":
              type = NilType
            elif contents == "table":
              type = TableType([])
            elif contents == "function":
              type = TypeConstructor("function", [new_type_var(), new_type_var(), new_type_var()], None, [])
            else:
              assert False, f"Not implemented: {contents}"
            res1 = intersect(arg_t, type)
            if res1 is None: return UnifyError(node.location, f"Attempting to narrow down type '{arg_t}' to '{type}' will result in a 'never' type")
            ctx.mapping[arg.name] = res1
            return None
      if isinstance(left, Var):
        res = infer(right, ctx)
        if isinstance(res, UnifyError): return res
        expr_s, expr_t = res
        expr_t = broaden(expr_t)
        res = infer(left, ctx)
        if isinstance(res, UnifyError): return res
        var_s, var_t = res
        var_t = broaden(var_t)
        res2 = intersect(var_t, expr_t)
        if res2 is None: return UnifyError(node.location, f"Attempting to compare two distinct types: '{var_t}' and '{expr_t}'")
        ctx.mapping[left.name] = res2
        return None
  return None

def infer(node: BaseNode, ctx: Context) -> UnifyResult:
  global global_ctx
  if isinstance(node, Var):
    if node.name in ctx.mapping:
      val = instantiate(ctx.mapping[node.name])
      return Substitution({}), val
    if node.name in global_ctx.mapping:
      val = instantiate(global_ctx.mapping[node.name])
      return Substitution({}), val
    return UnifyError(node.location, f"Unbound identifier: '{node.name}'")
  elif isinstance(node, Nil):
    return Substitution({}), TypeConstructor("nil", [], None, [])
  elif isinstance(node, Number):
    return Substitution({}), TypeConstructor("number", [], node.value, [])
  elif isinstance(node, String):
    return Substitution({}), TypeConstructor("string", [], node.value, [])
  elif isinstance(node, Boolean):
    return Substitution({}), TypeConstructor("boolean", [], node.value, [])
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
      types.append((k_type, v_type))
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
      checks: list[tuple[Expr, MonoType]] = []
      if isinstance(node.left, (Var, IndexExpr)):
        checks.append((node.left, right_t))
      if isinstance(node.right, (Var, IndexExpr)):
        checks.append((node.right, left_t))
      if isinstance(node.left, FuncCall) \
          and isinstance(node.left.func, Var) \
          and node.left.func.name == "type" \
          and "type" not in ctx.mapping \
          and len(node.left.args) == 1 \
          and isinstance(node.left.args[0], (Var, IndexExpr)) \
          and isinstance(node.right, String):
        if node.right.value == "number":
          checks.append((node.left.args[0], NumberType))
        if node.right.value == "string":
          checks.append((node.left.args[0], StringType))
        if node.right.value == "boolean":
          checks.append((node.left.args[0], BooleanType))
        if node.right.value == "nil":
          checks.append((node.left.args[0], NilType))
        if node.right.value == "table":
          checks.append((node.left.args[0], TableType))
        if node.right.value == "function":
          checks.append((node.left.args[0], TypeConstructor("function", [new_type_var(), new_type_var(), new_type_var()], None, [])))
      return left_s.apply_subst(right_s.apply_subst(s)), TypeConstructor("boolean", [], None, checks)
    elif node.op in ["and", "or"]:
      bool_left_s = unify(left_t, BooleanType)
      if isinstance(bool_left_s, str): return UnifyError(node.location, bool_left_s)
      bool_right_s = unify(right_t, BooleanType)
      if isinstance(bool_right_s, str): return UnifyError(node.location, bool_right_s)
      return bool_left_s.apply_subst(bool_right_s.apply_subst(left_s.apply_subst(right_s))), TypeConstructor("boolean", [], None, left_t.checks + right_t.checks)
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
    param_tuple = TypeConstructor("tuple", param_types, None, [])
    if node.annotation.ret_type is not None and node.name is not None:
      ctx.mapping[node.name] = TypeConstructor("function", [param_tuple, node.annotation.ret_type, NilType], None, [])
    res = infer(node.body, ctx)
    if isinstance(res, UnifyError): return res
    body_s, body_t = res
    params = body_s.apply_mono(param_tuple)
    if node.annotation.ret_type is not None:
      ret_anno_s = unify(body_t, node.annotation.ret_type)
      if isinstance(ret_anno_s, str): return UnifyError(node.location, ret_anno_s)
      body_t = ret_anno_s.apply_mono(node.annotation.ret_type)
    return body_s, TypeConstructor("function", [params, body_t, var], is_vararg, [])
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
    node_func_t = flatten_tuple(node_func_t)
    varargs: MonoType | None = None
    # TODO find a better way to do this
    if isinstance(node_func_t, TypeVariable):
      func_type = TypeConstructor("function", [TypeConstructor("tuple", [broaden(p) for p in params1], None, []), beta, NilType], None, [])
      subs = unify(func_type, node_func_t)
      if isinstance(subs, str): return UnifyError(node.location, subs)
      return subs.apply_subst(node_func_s.apply_subst(args_s)), subs.apply_subst(node_func_s).apply_mono(beta)
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
    func_type = TypeConstructor("function", [TypeConstructor("tuple", params1, None, []), beta, NilType], None, [])
    func_s = unify(func_type, node_func_t)
    if isinstance(func_s, str): return UnifyError(node.location, func_s)
    assert isinstance(node_func_t, TypeConstructor)
    replace_s = unify(node_func_t.args[0], TypeConstructor("tuple", params1, None, [])) 
    if isinstance(replace_s, str): return UnifyError(node.location, replace_s)
    if varargs is not None and node_func_t.args[2] != NilType:
      assert isinstance(node_func_t.args[2], TypeVariable)
      replace_s = Substitution({node_func_t.args[2].name: varargs}).apply_subst(replace_s)
    if isinstance(replace_s, str): return UnifyError(node.location, replace_s)
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
      res = infer(expr, ctx)
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
      s = expr_s.apply_subst(s)
    s.is_returning = True
    return s, TypeConstructor("tuple", exprs, None, [])
  elif isinstance(node, IfStmt):
    res = infer(node.cond, ctx)
    if isinstance(res, UnifyError): return res
    cond_s, cond_t = res
    bool_cond_s = unify(cond_t, BooleanType)
    base_ctx = ctx
    ctx = Context(ctx.mapping.copy())
    if isinstance(bool_cond_s, str): return UnifyError(node.location, bool_cond_s)
    if isinstance(cond_t, TypeConstructor):
      for prefix1, expr1 in cond_t.checks:
        res = infer(prefix1, ctx)
        if isinstance(res, UnifyError): return res
        prefix_s, prefix_t = res
        val1 = intersect(prefix_t, expr1)
        if val1 is None:
          return UnifyError(node.location, f"Attempting to narrow type '{prefix_t}' into '{expr1}' results in a 'never' type")
        if isinstance(prefix1, Var):
          ctx.mapping[prefix1.name] = val1
        else:
          err = set_path(prefix1, val1, ctx)
          if err: return err
    res = infer(node.body, ctx)
    if isinstance(res, UnifyError): return res
    body_s, body_t = res
    is_ret = body_s.is_returning
    if node.else_stmt:
      ctx = Context(base_ctx.mapping.copy())
      if isinstance(cond_t, TypeConstructor):
        for prefix1, expr1 in cond_t.checks:
          res = infer(prefix1, ctx)
          if isinstance(res, UnifyError): return res
          prefix_s, prefix_t = res
          val1 = subtract(prefix_t, expr1)
          if isinstance(prefix1, Var):
            ctx.mapping[prefix1.name] = val1
          else:
            err = set_path(prefix1, val1, ctx)
            if err: return err
      res = infer(node.else_stmt, ctx)
      if isinstance(res, UnifyError): return res
      else_s, else_t = res
      if is_ret and not else_s.is_returning:
        is_ret = False
      body_s = else_s.apply_subst(body_s)
      subs = unify(else_t, broaden(body_t))
      if isinstance(subs, str): subs = Substitution({})
      body_t = subs.apply_mono(smart_union(else_t, body_t))
    else:
      is_ret = False
    s = body_s.apply_subst(cond_s)
    s.is_returning = is_ret
    return s, cond_s.apply_mono(body_t)
  elif isinstance(node, Chunk):
    ctx = Context(ctx.mapping.copy())
    ret: MonoType | None = None
    s = Substitution({})
    has_returned = False
    for stmt in node.stmts:
      res = infer(stmt, ctx)
      if isinstance(res, UnifyError): return res
      stmt_s, stmt_t = res
      if isinstance(stmt_t, TypeConstructor) and stmt_t.name == "tuple" and not isinstance(stmt, FuncCall):
        if stmt_s.is_returning: has_returned = True
        if ret is None:
          ret = stmt_t
        #else:
        ret_s = unify(stmt_t, broaden(ret))
        if isinstance(ret_s, str):
          ret_s = Substitution({})
          # return UnifyError(node.location, ret_s)
        s = ret_s.apply_subst(s)
        assert isinstance(ret, TypeConstructor)
        assert isinstance(stmt_t, TypeConstructor)
        for i, arg1 in enumerate(stmt_t.args):
          if i >= len(ret.args):
            ret.args.append(UnionType(arg1, NilType))
          else:
            ret.args[i] = smart_union(ret.args[i], arg1)
        ret = ret_s.apply_mono(ret)
      s = stmt_s.apply_subst(s)
    if node.last:
      res = infer(node.last, ctx)
      if isinstance(res, UnifyError): return res
      stmt_s, stmt_t = res
      if not ret:
        ret = stmt_t
      else:
        ret_s = unify(stmt_t, broaden(ret))
        if isinstance(ret_s, str):
          ret_s = Substitution({})
          # return UnifyError(node.location, ret_s)
        ret = ret_s.apply_mono(broaden(ret))
        assert isinstance(stmt_t, TypeConstructor) and stmt_t.name == "tuple"
        assert isinstance(ret, TypeConstructor)
        for i, arg1 in enumerate(stmt_t.args):
          if i >= len(ret.args):
            ret.args.append(UnionType(arg1, NilType))
          else:
            ret.args[i] = smart_union(ret.args[i], arg1)
        s = ret_s.apply_subst(s)
      s = stmt_s.apply_subst(s)
    elif ret and not has_returned:
      new_ret = TypeConstructor("tuple", [], None, [])
      for arg in ret.args:
        new_ret.args.append(UnionType(arg, NilType))
      ret = new_ret
    s.is_returning = True
    if ret is None:
      s.is_returning = False
      ret = TypeConstructor("tuple", [], None, [])
    return s, ret
  assert False, f"Not implemented: {node}"

