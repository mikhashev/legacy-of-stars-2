-- HTTP Handler for AI Advisor analyze endpoint
local advisor_lib = require("advisor_lib")
local json = require("json")

local function handler(req, res)
  local body = json.decode(req:body())
  local result = advisor_lib.analyze(body)
  res:set_status(200)
  res:set_header("Content-Type", "application/json")
  res:write(json.encode(result))
end

return {
  handler = handler
}
