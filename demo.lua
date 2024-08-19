
function change_person(p)
  local new = {
    name = "@" .. p.name,
    age = p.age + 1,
  }
  new.height = p.x + p.y
  return new
end

return change_person({
  name = "Ian",
  age = 15,
  x = 0,
  y = 0,
})
