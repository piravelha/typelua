from dataclasses import dataclass
from typing import TypeAlias, Any

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

@dataclass
class TypeConstructor:
  name: str
  args: list[MonoType]
  value: Any

NumberType = TypeConstructor("number", [], None)
StringType = TypeConstructor("string", [], None)
BooleanType = TypeConstructor("boolean", [], None)

@dataclass
class TableType:
  fields: list[tuple[MonoType, MonoType]]

@dataclass
class ForallType:
  var: str
  body: PolyType

@dataclass
class Context:
  mapping: dict[str, PolyType]
