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
  assert False, f"Not implemented: {node}"
