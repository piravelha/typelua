function union()
  if true then
    return {x = 0, z = true}
  end
  return {x = "", y = 1}
end

local res = union()

if type(res.z) == "nil" and type(res.x) == "string" then
  return res.z, res.x
end

return nil, 123
