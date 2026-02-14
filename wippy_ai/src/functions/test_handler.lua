-- Simple test handler without external dependencies
local http = require("http")

local function handler()
    local res = http.response()
    res:set_status(200)
    res:write_json({ message = "Hello from Wippy!", status = "ok" })
end

return { handler = handler }
