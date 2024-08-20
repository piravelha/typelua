
function new_person(name, age)
  if type(name) == "string" and type(age) == "number" then
    return {
      name = name,
      age = age,
    }
  end
  return nil
end

--@reveal new_person