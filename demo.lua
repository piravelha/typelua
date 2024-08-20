local unknown = (function()
  if true then return 1 else return "a" end
end)()

return unknown
