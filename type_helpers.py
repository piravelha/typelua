from dataclasses import dataclass
from typing import Optional, TypeVar, TypeAlias
from type_models import *

T = TypeVar("T")
Result: TypeAlias = str | T

@dataclass
class Substitution:
  mapping: dict[str, MonoType]
  def __init__(self, mapping: dict[str, MonoType], is_returning: bool = False) -> None:
    self.mapping = mapping
    self.is_returning = is_returning
  is_returning: bool
  def apply_mono(self, m: MonoType) -> MonoType:
    if isinstance(m, TypeVariable):
      if m.name in self.mapping:
        return self.apply_mono(self.mapping[m.name])
      return m
    elif isinstance(m, TypeConstructor):
      return TypeConstructor(m.name, [self.apply_mono(a) for a in m.args], m.value, m.checks)
    elif isinstance(m, TableType):
      return TableType([(a, self.apply_mono(b)) for a, b in m.fields])
    elif isinstance(m, UnionType):
      return UnionType(self.apply_mono(m.left), self.apply_mono(m.right))
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
        res = intersect(t, new[n])
        #if not res:
        #  res = t
        assert res
        new[n] = res
      else:
        new[n] = self.apply_mono(t)
    return Substitution(new, self.is_returning or s.is_returning)
  def apply_subst_unsafe(self, s: 'Substitution') -> 'Substitution':
    new = self.mapping.copy()
    for n, t in s.mapping.items():
      new[n] = self.apply_mono(t)
    return Substitution(new, self.is_returning or s.is_returning)

var_count = 0
def new_type_var() -> TypeVariable:
  global var_count
  var_count += 1
  return TypeVariable(f"t{var_count}")

def intersect(type1: MonoType, type2: MonoType) -> 'Optional[MonoType]':
  if isinstance(type1, TypeVariable):
    return type2
  if isinstance(type2, TypeVariable):
    return type1
  if isinstance(type2, UnionType):
    return intersect(type1, type2.left) or intersect(type1, type2.right)
  if isinstance(type1, UnionType):
    return intersect(type2, type1)
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    fields = type1.fields + type2.fields
    filtered = []
    for k, v in fields:
      for fk, fv in filtered:
        if extends(k, fk):
          break
      else:
        filtered.append((k, v))
    return TableType(filtered)
  if isinstance(type1, TypeVariable) and isinstance(type2, TypeVariable):
    if type1.name != type2.name:
      return None
    return type1
  if isinstance(type1, TypeConstructor) and isinstance(type2, TypeConstructor):
    if type1.name != type2.name:
      return None
    args = []
    for a, b in zip(type1.args, type2.args):
      val = intersect(a, b)
      if not val: return None
      args.append(val)
    return TypeConstructor(type1.name, args, type1.value, type1.checks + type2.checks)
  return None

def subtract(type1: MonoType, type2: MonoType) -> MonoType:
  if isinstance(type1, UnionType):
    if extends(type1.left, type2):
      return subtract(type1.right, type2)
    if extends(type1.right, type2):
      return subtract(type1.left, type2)
    return UnionType(subtract(type1.left, type2), subtract(type1.right, type2))
  return type1

def instantiate(type: PolyType, mappings: dict[str, TypeVariable] = {}) -> MonoType:
  if isinstance(type, TypeVariable):
    if type.name in mappings:
      return mappings[type.name]
    return type
  elif isinstance(type, TypeConstructor):
    return TypeConstructor(type.name, [instantiate(a, mappings) for a in type.args], type.value, type.checks)
  elif isinstance(type, TableType):
    return TableType([(instantiate(k, mappings), instantiate(v, mappings)) for k, v in type.fields])
  elif isinstance(type, UnionType):
    return UnionType(instantiate(type.left), instantiate(type.right))
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
  elif isinstance(type, UnionType):
    return free_vars_of_type(type.left) | free_vars_of_type(type.right)
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
  if isinstance(type1, UnionType):
    left_s = unify(type1.left, type2)
    if isinstance(left_s, str): return left_s
    right_s = unify(type1.right, type2)
    if isinstance(right_s, str): return right_s
    return left_s.apply_subst(right_s)
  if isinstance(type2, UnionType):
    s = Substitution({})
    left_s = unify(type1, type2.left)
    if isinstance(left_s, Substitution):
      s = left_s.apply_subst(s)
    right_s = unify(type1, type2.right)
    if isinstance(right_s, Substitution):
      s = right_s.apply_subst(s)
    if isinstance(left_s, str) and isinstance(right_s, str): return left_s
    return s
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    s = Substitution({})
    for (k1, v1) in type1.fields:
      v: 'MonoType | None' = None
      for k2, v2 in type2.fields:
        if extends(k1, k2):
          v = v2
          break
      if v is None: return f"Field `{k2}` expected on type `{type1}`, but was not found"
      v_res = unify(v, v1)
      if isinstance(v_res, str): return v_res
      s = v_res.apply_subst(s)
    return s
  if not isinstance(type1, TypeConstructor) or not isinstance(type2, TypeConstructor):
    return f"Types dont unify: `{type1}` and `{type2}`"
  if type1.name != type2.name:
    return f"Types dont unify: Expected `{type2.name}`, got `{type1.name}`"
  # if type1.name == "tuple" and type2.name == "tuple":
  #   s = Substitution({})
  #   for a, b in zip(type1.args, type2.args):
  #     res = unify(a, b)
  #     if isinstance(res, str): return res
  #     s = res.apply_subst(res)
  #   return s
  if len(type1.args) != len(type2.args):
    return f"Types dont unify: Expected `{type1}`, but got `{type2}`" 
  if type1.value is not None and type2.value is not None:
    if type1.value != type2.value:
      return f"Type `{type1}` does not extend type `{type2}`" 
  if type1.name == "function":
    s = Substitution({})
    assert isinstance(type1.args[0], TypeConstructor)
    assert isinstance(type2.args[0], TypeConstructor)
    for p1, p2 in zip(type1.args[0].args, type2.args[0].args):
      res = unify(p2, p1)
      if isinstance(res, str): return res
      s = res.apply_subst(s)
    if not isinstance(type1.args[1], (TypeConstructor, TypeVariable)) or type1.args[1].name != "tuple" and not isinstance(type1.args[1], TypeVariable):
      type1.args[1] = TypeConstructor("tuple", [type1.args[1]], None, [])
    if not isinstance(type2.args[1], (TypeConstructor, TypeVariable)) or type2.args[1].name != "tuple" and not isinstance(type1.args[1], TypeVariable):
      type2.args[1] = TypeConstructor("tuple", [type2.args[1]], None, [])
    res = unify(type1.args[1], type2.args[1])
    if isinstance(res, str): return res
    return res.apply_subst(s)
  if type2.value is not None and type1.value is None:
    if type2.value is True:
      assert False
    return f"Type `{type1}` does not extend type `{type2}`"
  s = Substitution({})
  for a, b in zip(type1.args, type2.args):
    res = unify(a, b)
    if isinstance(res, str): return res
    s = res.apply_subst(res)
  return s

def broaden(type: MonoType) -> MonoType:
  if isinstance(type, TypeConstructor):
    return TypeConstructor(type.name, [broaden(a) for a in type.args], None, type.checks)
  if isinstance(type, UnionType):
    return UnionType(broaden(type.left), broaden(type.right))
  return type

def flatten_tuple(type: MonoType) -> MonoType:
  if isinstance(type, TypeConstructor) and type.name == "tuple":
    return flatten_tuple(type.args[0])
  return type

def smart_union(type1: MonoType, type2: MonoType) -> MonoType:
  if isinstance(type1, TypeVariable) and isinstance(type2, TypeVariable) and type1.name == type2.name:
    return type1
  if isinstance(type1, TypeConstructor) and isinstance(type2, TypeConstructor):
    if type1.name == type2.name:
      return TypeConstructor(type1.name, [smart_union(a, b) for a, b in zip(type1.args, type2.args)], type1.value, type1.checks + type2.checks)
    return UnionType(type1, type2)
  if isinstance(type1, TableType) and isinstance(type2, TableType):
    fields: list[tuple[MonoType, MonoType]] = []
    for k1, v1 in type1.fields:
      val = None
      for k2, v2 in type2.fields:
        if extends(k1, k2):
          val = v2
      for fk, fv in fields:
        if extends(k1, fk):
          break
      else:
        if not val:
          fields.append((k1, smart_union(v1, NilType)))
        else:
          fields.append((k1, smart_union(v1, val)))
    for k1, v1 in type2.fields:
      val = None
      for k2, v2 in type1.fields:
        if extends(k1, k2):
          val = v2
      for fk, fv in fields:
        if extends(k1, fk):
          break
      else:
        if not val:
          fields.append((k1, smart_union(v1, NilType)))
        else:
          fields.append((k1, smart_union(v1, val)))
    return TableType(fields)
  return UnionType(type1, type2)

def extends(type1, type2):
  if isinstance(type1, TypeVariable):
    return isinstance(type2, TypeVariable) and type1.name == type2.name
  if isinstance(type2, TypeVariable):
    return isinstance(type1, TypeVariable) and type2.name == type1.name
  return not isinstance(unify(type1, type2), str)
