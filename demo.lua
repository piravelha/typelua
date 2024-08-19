
function factorial(x)
  --@return number
  if x .. "!" == "a!" then
    return 1
  end
  return #x + factorial(x)
end

return function(x, y)
  return factorial(x .. tostring(y))
end

