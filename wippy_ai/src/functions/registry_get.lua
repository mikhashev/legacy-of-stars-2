-- HTTP Handler for Registry get endpoint
local http = require("http")
local registry_state = require("registry_state")

local function handler()
  local req = http.request()
  local res = http.response()

  -- Parse query parameters from the path
  local query = req:query()
  local key = query.key
  if key then
    local value = registry_state.get(key)
    res:set_status(200)
    res:write_json({key = key, value = value})
  else
    res:set_status(400)
    res:write_json({error = "Missing key parameter"})
  end
end

return {
  handler = handler
}
