from dataclasses import dataclass
from typing import Optional
from type_models import *

@dataclass
class Substitution:
  mapping: dict[str, MonoType]
  def apply_mono(self, m: MonoType) -> MonoType:
    if isinstance(m, TypeVariable):
      if m.name in self.mapping:
        return self.mapping[m.name]
      return m
    elif isinstance(m, TypeConstructor):
      return TypeConstructor(m.name, [self.apply_mono(a) for a in m.args], m.value)
    assert False, f"Unknown type: {m}"
  def apply_poly(self, p: PolyType) -> PolyType:
    if isinstance(p, (TypeVariable, TypeConstructor)):
      res: MonoType = self.apply_mono(p)
      if isinstance(res, (TypeVariable, TypeConstructor)):
        return res
      assert False
    elif isinstance(p, ForallType):
      return ForallType(p.var, self.apply_poly(p.body))
    assert False
  def apply_subst(self, s: 'Substitution') -> 'Substitution':
    new = self.mapping.copy()
    for n, t in s.mapping.items():
      new[n] = self.apply_mono(t)
    return Substitution(new)

var_count = 0
def new_type_var() -> TypeVariable:
  global var_count
  var_count += 1
  return TypeVariable(f"t{var_count}")

def instantiate(type: PolyType, mappings: dict[str, TypeVariable] = {}) -> MonoType:
  if isinstance(type, TypeVariable):
    if type.name in mappings:
      return mappings[type.name]
    return type
  elif isinstance(type, TypeConstructor):
    return TypeConstructor(type.name, [instantiate(a, mappings) for a in type.args], type.value)
  elif isinstance(type, TableType):
    return TableType([(instantiate(k, mappings), instantiate(v, mappings)) for k, v in type.fields])
  elif isinstance(type, ForallType):
    mappings[type.var] = new_type_var()
    return instantiate(type.body, mappings)
  assert False

def free_vars_of_type(type: PolyType) -> set[str]:
  if isinstance(type, TypeVariable):
    return {type.name}
  elif isinstance(type, TypeConstructor):
    return {v for arg in type.args for v in free_vars_of_type(arg)}
  elif isinstance(type, TableType):
    return {x for k, v in type.fields for x in free_vars_of_type(k) | free_vars_of_type(v)}
  elif isinstance(type, ForallType):
    return free_vars_of_type(type.body) - {type.var}

def free_vars_of_ctx(ctx: Context) -> set[str]:
  return {v for type in ctx.mapping.values() for v in free_vars_of_type(type)}

def generalize(type: MonoType, ctx: Context) -> PolyType:
  fv = free_vars_of_type(type) - free_vars_of_ctx(ctx)
  poly: PolyType = type
  for v in fv:
    poly = ForallType(v, poly)
  return poly

def unify(type1: MonoType, type2: MonoType) -> Optional[Substitution]:
  if isinstance(type1, TypeVariable) and isinstance(type2, TypeVariable) and type1.name == type2.name:
    return Substitution({})
  if isinstance(type2, TypeVariable):
    return Substitution({type2.name: type1})
  if isinstance(type1, TypeVariable):
    return Substitution({type1.name: type2})
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    s = Substitution({})
    for (k1, v1) in type2.fields:
      v: 'MonoType | None' = None
      for k2, v2 in type1.fields:
        if unify(k1, k2) is not None:
          v = v2
          break
      if v is None: return v
      v_res = unify(v1, v)
      if not v_res: return v_res
      s = v_res.apply_subst(s)
    return s
  if not isinstance(type1, TypeConstructor) or not isinstance(type2, TypeConstructor):
    return None
  if type1.name != type2.name:
    return None
  if len(type1.args) != len(type2.args):
    return None
  if type1.value is not None and type2.value is not None:
    if type1.value != type2.value:
      return None
  s = Substitution({})
  for a, b in zip(type1.args, type2.args):
    res = unify(a, b)
    if not res: return res
    s = res.apply_subst(res)
  return s
