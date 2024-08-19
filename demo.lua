
-- (((a) -> b), a) -> b
function apply(x, y)
  return x(y)
end

-- (string) -> string
function f(x)
  return x .. "!"
end

-- (number) -> number
function g(y)
  return y + 1
end

-- (string, number)
return apply(f, "!"), apply(g, 10)


