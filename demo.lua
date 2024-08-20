local unknown = (function()
  if true then return 1 else return "a" end
end)()
if type(unknown) == "number" then
  return unknown
end
return 0