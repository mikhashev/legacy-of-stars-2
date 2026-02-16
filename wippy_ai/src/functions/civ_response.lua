-- HTTP Handler for Civilization Response generate endpoint
local http = require("http")
local civ_response = require("civ_response_lib")

local function handler()
  local req = http.request()
  local res = http.response()

  local body, err = req:body_json()
  if err then
    res:set_status(400)
    res:write_json({error = "Invalid JSON: " .. tostring(err)})
    return
  end
  local result = civ_response.generate(body)
  res:set_status(200)
  res:write_json(result)
end

return {
  handler = handler
}
