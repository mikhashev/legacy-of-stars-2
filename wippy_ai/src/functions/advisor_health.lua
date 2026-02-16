-- HTTP Handler for AI Advisor health endpoint
local http = require("http")

local function handler()
  local res = http.response()
  -- Simple health check without library dependencies
  res:set_status(200)
  res:write_json({
    status = "healthy",
    service = "legacy-of-stars-ai",
    version = "1.0.0"
  })
end

return {
  handler = handler
}
