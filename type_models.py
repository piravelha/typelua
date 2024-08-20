from dataclasses import dataclass
from typing import Literal, TypeAlias, Any, cast
from models import Expr

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

variable_names_rendered = {}

@dataclass
class TypeVariable:
  name: str
  def __repr__(self) -> str:
    global variable_names_rendered
    if self.name in variable_names_rendered:
      return variable_names_rendered[self.name]
    letters = "abcdefghijklmnopqrstuvwyxz"
    if (i := len(variable_names_rendered)) < len(letters):
      variable_names_rendered[self.name] = letters[i]
      return letters[i]
    return self.name

@dataclass
class TypeConstructor:
  name: str
  args: list[MonoType]
  value: Any
  checks: list[tuple[Expr, MonoType]]
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
      params = ", ".join([str(a) for a in cast(TypeConstructor, self.args[0]).args] + (["..." + str(self.args[2])] if self.value else []))
      rets = ", ".join(f"{r}" for r in self.args[1].args) if isinstance(self.args[1], TypeConstructor) and self.args[1].name == "tuple" else repr(self.args[1])
      return f"({params}) -> {rets}"
    if self.name == "tuple":
      if len(self.args) == 1:
        return str(self.args[0])
      return "(" + ", ".join(str(a) for a in self.args) + ")"
    if self.args:
      args = ", ".join(str(a) for a in self.args)
      return f"{self.name}<{args}>"
    return self.name

NumberType = TypeConstructor("number", [], None, [])
StringType = TypeConstructor("string", [], None, [])
BooleanType = TypeConstructor("boolean", [], None, [])
NilType = TypeConstructor("nil", [], None, [])

def array_repr(table: 'TableType') -> str | Literal[False]:
  from type_helpers import unify, broaden
  types = list(map(lambda f: f[1], table.fields))
  filtered: list[MonoType] = []
  for type in types:
    for filt in filtered:
      if not isinstance(unify(type, filt), str):
        break
    else:
      filtered.append(broaden(type))
  strs = [repr(f) for f in filtered]
  if len(strs) > 1:
    return False
  if len(strs) == 1:
    return f"{strs[0]}[]"
  return f"[]"

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

typeof = type

@dataclass
class UnionType:
  left: MonoType
  right: MonoType
  def collect(self) -> list[MonoType]:
    left = [self.left]
    if isinstance(self.left, UnionType):
      left = self.left.collect()
    right = [self.right]
    if isinstance(self.right, UnionType):
      right = self.right.collect()
    return left + right
  def __repr__(self) -> str:
    if isinstance(self.left, TypeConstructor) and self.left.name == "nil":
      right = f"{self.right}"
      return f"({right})?" if " " in right else f"{right}?"
    if isinstance(self.right, TypeConstructor) and self.right.name == "nil":
      left = f"{self.left}"
      return f"({left})?" if " " in left else f"{left}?"
    
    #return f"({self.left}) | ({self.right})"
    from type_helpers import unify
    types = self.collect()
    filtered: list[MonoType] = []
    for type in types:
      for filt in filtered:
        if isinstance(filt, TypeVariable) and isinstance(type, TypeVariable) and filt.name == type.name:
          break
        if isinstance(filt, TypeVariable):
          continue
        if isinstance(type, TypeVariable):
          continue
        if not isinstance((s := unify(type, filt)), str):
          break
      else:
        filtered.append(type)
    return " | ".join(f"({f})" if ((s := f"{f}") and " " in s and not s.startswith("{")) else f"{f}" for f in filtered)

@dataclass
class ForallType:
  var: str
  body: PolyType
  def __repr__(self) -> str:
    return f"forall {self.var}. {self.body}"

@dataclass
class Context:
  mapping: dict[str, PolyType]
