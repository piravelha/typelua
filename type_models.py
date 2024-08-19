from dataclasses import dataclass
from typing import TypeAlias, Any, cast

MonoType: TypeAlias = """
  TypeVariable
  | TypeConstructor
  | TableType
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
      return "(" + ", ".join(str(a) for a in self.args) + ")"
    if self.args:
      args = ", ".join(str(a) for a in self.args)
      return f"{self.name}<{args}>"
    return self.name

NumberType = TypeConstructor("number", [], None)
StringType = TypeConstructor("string", [], None)
BooleanType = TypeConstructor("boolean", [], None)
NilType = TypeConstructor("nil", [], None)

@dataclass
class TableType:
  fields: list[tuple[MonoType, MonoType]]
  def __repr__(self) -> str:
    s = "{"
    for i, (k, v) in enumerate(self.fields):
      if i > 0:
        s += ", "
      if isinstance(k, TypeConstructor) and k.name == "string" and k.value is not None:
        s += f"{k.value}: {v}"
      else:
        s += f"[{k}]: {v}"
    return s + "}"

@dataclass
class ForallType:
  var: str
  body: PolyType
  def __repr__(self) -> str:
    return f"forall {self.var}. {self.body}"

@dataclass
class Context:
  mapping: dict[str, PolyType]
