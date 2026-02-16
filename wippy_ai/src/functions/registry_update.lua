-- HTTP Handler for Registry update endpoint
local http = require("http")
local registry_state = require("registry_state")

local function handler()
  local req = http.request()
  local res = http.response()

  local body, err = req:body_json()
  if err then
    res:set_status(400)
    res:write_json({error = "Invalid JSON: " .. tostring(err)})
    return
  end
  if body.key and body.value ~= nil then
    registry_state.set(body.key, body.value)
    res:set_status(200)
    res:write_json({success = true})
  else
    res:set_status(400)
    res:write_json({error = "Missing key or value"})
  end
end

return {
  handler = handler
}
