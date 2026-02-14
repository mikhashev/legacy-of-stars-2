-- HTTP Handler for AI Advisor health endpoint
local http = require("http")
local advisor_lib = require("advisor_lib")

local function handler()
    local res = http.response()

    local result = advisor_lib.health()

    res:set_status(200)
    res:write_json(result)
end

return { handler = handler }
