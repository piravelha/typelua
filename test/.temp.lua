
      function vararg(...)
        return ({...})[1]
      end
      local x = vararg(1, 2, 3)
      return x
    