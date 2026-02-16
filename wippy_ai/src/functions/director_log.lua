-- HTTP Handler for Director Log narrate endpoint
local http = require("http")
local director_log = require("director_log_lib")

local function handler()
  local req = http.request()
  local res = http.response()

  local body, err = req:body_json()
  if err then
    res:set_status(400)
    res:write_json({error = "Invalid JSON: " .. tostring(err)})
    return
  end
  local result = director_log.narrate(body)
  res:set_status(200)
  res:write_json(result)
end

return {
  handler = handler
}
