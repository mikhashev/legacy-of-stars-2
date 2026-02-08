-- HTTP Handler for AI Advisor health endpoint
local advisor_lib = require("advisor_lib")
local json = require("json")

local function handler(req, res)
  local result = advisor_lib.health()
  res:set_status(200)
  res:set_header("Content-Type", "application/json")
  res:write(json.encode(result))
end

return {
  handler = handler
}
