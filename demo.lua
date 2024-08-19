
function factorial(x)
  --@return number | boolean
  if x .. "!" == "a!" then
    return false
  end
  return #x + factorial(x)
end

return function(x, y)
  return factorial(x .. tostring(y))
end

