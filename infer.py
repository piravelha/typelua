from models import *
from type_models import *
from typing import Optional
from type_helpers import *

def infer(node: BaseNode, ctx: Context) -> Optional[tuple[Substitution, MonoType]]:
  if isinstance(node, Var):
    if node.name in ctx.mapping:
      val = instantiate(ctx.mapping[node.name])
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
  elif isinstance(node, FuncExpr):
    param_types: list[MonoType] = []
    ctx = Context(ctx.mapping.copy())
    for param in node.params:
      var = new_type_var()
      ctx.mapping[param] = var
      param_types.append(var)
    is_vararg = False
    if node.is_vararg:
      is_vararg = True
      var = new_type_var()
      ctx.mapping["..."] = var
    param_tuple = TypeConstructor("tuple", param_types, None)
    res = infer(node.body, ctx)
    if res is None: return res
    body_s, body_t = res
    params = body_s.apply_mono(param_tuple)
    return body_s, TypeConstructor("function", [params, body_t], False)
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
    func_type = TypeConstructor("function", [TypeConstructor("tuple", params1, None), beta], None)
    res = infer(node.func, ctx)
    if res is None: return res
    node_func_s, node_func_t = res
    func_s = unify(node_func_t, func_type)
    if func_s is None: return func_s
    assert isinstance(node_func_t, TypeConstructor)
    replace_s = unify(node_func_t.args[0], TypeConstructor("tuple", params1, None))
    return replace_s.apply_subst(func_s.apply_subst(node_func_s.apply_subst(args_s))), replace_s.apply_subst(func_s.apply_subst(node_func_s)).apply_mono(beta)
  assert False, f"Not implemented: {node}"

