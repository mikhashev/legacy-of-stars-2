-- HTTP Handler for Director Log narrate endpoint
local director_log = require("director_log_lib")
local json = require("json")

local function handler(req, res)
  local body = json.decode(req:body())
  local result = director_log.narrate(body)
  res:set_status(200)
  res:set_header("Content-Type", "application/json")
  res:write(json.encode(result))
end

return {
  handler = handler
}
