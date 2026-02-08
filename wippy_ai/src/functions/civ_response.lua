-- HTTP Handler for Civilization Response generate endpoint
local civ_response = require("civ_response_lib")
local json = require("json")

local function handler(req, res)
  local body = json.decode(req:body())
  local result = civ_response.generate(body)
  res:set_status(200)
  res:set_header("Content-Type", "application/json")
  res:write(json.encode(result))
end

return {
  handler = handler
}
