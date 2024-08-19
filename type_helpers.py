from dataclasses import dataclass
from typing import Optional, TypeVar, TypeAlias
from type_models import *

T = TypeVar("T")
Result: TypeAlias = str | T

@dataclass
class Substitution:
  mapping: dict[str, MonoType]
  def apply_mono(self, m: MonoType) -> MonoType:
    if isinstance(m, TypeVariable):
      if m.name in self.mapping:
        return self.apply_mono(self.mapping[m.name])
      return m
    elif isinstance(m, TypeConstructor):
      return TypeConstructor(m.name, [self.apply_mono(a) for a in m.args], m.value)
    elif isinstance(m, TableType):
      return TableType([(a, self.apply_mono(b)) for a, b in m.fields])
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
      if new.get(n):
        new[n] = intersect(t, new[n])
      else:
        new[n] = self.apply_mono(t)
    return Substitution(new)
  def apply_subst_unsafe(self, s: 'Substitution') -> 'Substitution':
    new = self.mapping.copy()
    for n, t in s.mapping.items():
      new[n] = self.apply_mono(t)
    return Substitution(new)



var_count = 0
def new_type_var() -> TypeVariable:
  global var_count
  var_count += 1
  return TypeVariable(f"t{var_count}")

def intersect(type1: MonoType, type2: MonoType) -> MonoType:
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    fields = type1.fields + type2.fields
    return TableType(fields)
  if isinstance(type1, TypeVariable) and isinstance(type2, TypeVariable):
    if type1.name != type2.name:
      print(f"(DEBUG 0) Never type detected")
      #exit(1)
    return type1
  if isinstance(type1, TypeConstructor) and isinstance(type2, TypeConstructor):
    if type1.name != type2.name:
      print(f"(DEBUG 1) Never type detected")
      #exit(1)
    args = []
    for a, b in zip(type1.args, type2.args):
      args.append(intersect(a, b))
    return TypeConstructor(type1.name, args, type1.value)
  print(f"(DEBUG 2) Never type detected")
  #exit(1)

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

def unify(type1: MonoType, type2: MonoType) -> Result[Substitution]:
  if isinstance(type1, TypeVariable) and isinstance(type2, TypeVariable) and type1.name == type2.name:
    return Substitution({})
  if isinstance(type2, TypeVariable):
    return Substitution({type2.name: type1})
  if isinstance(type1, TypeVariable):
    return Substitution({type1.name: type2})
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    s = Substitution({})
    for (k1, v1) in type1.fields:
      v: 'MonoType | None' = None
      for k2, v2 in type2.fields:
        if not isinstance(unify(k1, k2), str):
          v = v2
          break
      if v is None: return f"Field '{k1}' expected on type '{type2}', but was not found"
      v_res = unify(v, v1)
      if isinstance(v_res, str): return v_res
      s = v_res.apply_subst(s)
    return s
  if not isinstance(type1, TypeConstructor) or not isinstance(type2, TypeConstructor):
    return f"Types dont unify: '{type1}' and '{type2}'"
  if type1.name != type2.name:
    return f"Names of types dont match: Expected '{type2.name}', got '{type1.name}'"
  if len(type1.args) != len(type2.args):
    return f"Generic types have a different count of generic arguments: '{type1}' and '{type2}'" 
  if type1.value is not None and type2.value is not None:
    if type1.value != type2.value:
      return f"Type '{type1}' does not extend type '{type2}'" 
  if type1.name == "function":
    s = Substitution({})
    assert isinstance(type1.args[0], TypeConstructor)
    assert isinstance(type2.args[0], TypeConstructor)
    for p1, p2 in zip(type1.args[0].args, type2.args[0].args):
      res = unify(p2, p1)
      if isinstance(res, str): return res
      s = res.apply_subst(s)
    res = unify(type1.args[1], type2.args[1])
    if isinstance(res, str): return res
    return res.apply_subst(s)
  if type2.value is not None and type1.value is None:
    return f"Type '{type1}' does not extend type '{type2}'"
  s = Substitution({})
  for a, b in zip(type1.args, type2.args):
    res = unify(a, b)
    if isinstance(res, str): return res
    s = res.apply_subst(res)
  return s

def broaden(type: MonoType) -> MonoType:
  if isinstance(type, TypeConstructor):
    return TypeConstructor(type.name, [broaden(a) for a in type.args], None)
  return type
