-- HTTP Handler for Registry update endpoint
local registry_state = require("registry_state")
local json = require("json")

local function handler(req, res)
  local body = json.decode(req:body())
  if body.key and body.value ~= nil then
    registry_state.set(body.key, body.value)
    res:set_status(200)
    res:set_header("Content-Type", "application/json")
    res:write(json.encode({success = true}))
  else
    res:set_status(400)
    res:set_header("Content-Type", "application/json")
    res:write(json.encode({error = "Missing key or value"}))
  end
end

return {
  handler = handler
}
