from type_helpers import *
from models import *
from type_models import *

def fn(params: MonoType, returns: MonoType, var: MonoType) -> MonoType:
  return TypeConstructor("function", [params, returns, var], None)

def tup(*types: MonoType) -> MonoType:
  return TypeConstructor("tuple", list(types), None)

var = TypeVariable

tostring_a = new_type_var()

ctx: Context = Context({
  "tostring": fn(tup(tostring_a), tup(StringType), NilType)
})
