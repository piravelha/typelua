from dataclasses import dataclass
from typing import Literal, TypeAlias, Any, cast

MonoType: TypeAlias = """
  TypeVariable
  | TypeConstructor
  | TableType
  | UnionType
"""

PolyType: TypeAlias = """
  MonoType
  | ForallType
"""

@dataclass
class TypeVariable:
  name: str
  def __repr__(self) -> str:
    return self.name

@dataclass
class TypeConstructor:
  name: str
  args: list[MonoType]
  value: Any
  def __repr__(self) -> str:
    if self.name == "string" and self.value is not None:
      return "\"" + str(self.value) + "\""
    if self.name == "number" and self.value is not None:
      if self.value % 1 == 0:
        return str(int(self.value))
      return str(self.value)
    if self.name == "boolean" and self.value is not None:
      return self.value and "true" or "false"
    if self.name == "function":
      vararg: list[str] = ["..."] if self.value else []
      params = ", ".join([str(a) for a in cast(TypeConstructor, self.args[0]).args] + vararg)
      rets = ", ".join(str(r) for r in self.args[1].args) if isinstance(self.args[1], TypeConstructor) else repr(self.args[1])
      return f"({params}) -> {rets}"
    if self.name == "tuple":
      if len(self.args) == 1:
        return str(self.args[0])
      return "(" + ", ".join(str(a) for a in self.args) + ")"
    if self.args:
      args = ", ".join(str(a) for a in self.args)
      return f"{self.name}<{args}>"
    return self.name

NumberType = TypeConstructor("number", [], None)
StringType = TypeConstructor("string", [], None)
BooleanType = TypeConstructor("boolean", [], None)
NilType = TypeConstructor("nil", [], None)

def array_repr(table: 'TableType') -> str | Literal[False]:
  from type_helpers import unify, broaden
  types = list(map(lambda f: f[1], table.fields))
  filtered = []
  for type in types:
    for filt in filtered:
      if not isinstance(unify(type, filt), str):
        break
    else:
      filtered.append(broaden(type))
  filtered = [repr(f) for f in filtered]
  if len(filtered) > 1:
    return False
  if len(filtered) == 1:
    return f"{filtered[0]}[]"
  return f"()[]"

def is_array(table: 'TableType') -> bool:
  for k, v in table.fields:
    if not isinstance(k, TypeConstructor) or k.name != "number":
      return False
  return True

@dataclass
class TableType:
  fields: list[tuple[MonoType, MonoType]]
  def __repr__(self) -> str:
    if is_array(self):
      if (r := array_repr(self)) is not False:
        return r
    s = "{"
    for i, (k, v) in enumerate(self.fields):
      if i > 0:
        s += ", "
      if isinstance(k, TypeConstructor) and k.name == "string" and k.value is not None:
        s += f"{k.value}: {v}"
      else:
        s += f"[{k}]: {v}"
    s += "}"
    max_repr = 100
    if len(s) > max_repr:
      left = s[:int(max_repr/2)]
      right = s[-int(max_repr/2):]
      return left + "....." + right
    return s

@dataclass
class UnionType:
  left: MonoType
  right: MonoType
  def __repr__(self) -> str:
    from type_helpers import unify
    if not isinstance(unify(self.left, self.right), str):
      return repr(self.right)
    if not isinstance(unify(self.right, self.left), str):
      return repr(self.left)
    return f"{self.left} | {self.right}"

@dataclass
class ForallType:
  var: str
  body: PolyType
  def __repr__(self) -> str:
    return f"forall {self.var}. {self.body}"

@dataclass
class Context:
  mapping: dict[str, PolyType]
