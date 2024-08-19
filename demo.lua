
function factorial(x)
  --@return string
  if x <= 1 then
    return 1
  end
  return x * factorial(x - 1)
end

return factorial
