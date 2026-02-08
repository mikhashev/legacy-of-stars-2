-- HTTP Handler for Registry get endpoint
local registry_state = require("registry_state")
local json = require("json")

local function handler(req, res)
  -- Parse query parameters from the path
  local query = req:query()
  local key = query.key
  if key then
    local value = registry_state.get(key)
    res:set_status(200)
    res:set_header("Content-Type", "application/json")
    res:write(json.encode({key = key, value = value}))
  else
    res:set_status(400)
    res:set_header("Content-Type", "application/json")
    res:write(json.encode({error = "Missing key parameter"}))
  end
end

return {
  handler = handler
}
