
function factorial(x)
  --@return number
  if x <= 1 then
    return 1
  end
  return x * factorial(x - 1)
end

return factorial
