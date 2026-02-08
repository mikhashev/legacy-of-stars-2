-- Director Log Narrator Process for Legacy of Stars
-- Generates narrative summaries of each generation as the Director's Log

local http = require("http")
local json = require("json")
local llm = require("llm_client")

local M = {}

local process_id = nil
local request_count = 0

-- Generate a Director's Log entry for a generation
function M.narrate(params)
  request_count = request_count + 1

  local generation = params.generation or 1
  local year = params.year or 1977
  local events = params.events or {}
  local game_state = params.game_state or {}

  -- Build event summary
  local event_summary = ""

  if #events > 0 then
    local event_parts = {}
    for _, event in ipairs(events) do
      table.insert(event_parts, string.format("- %s", event.description or event.type))
    end
    event_summary = table.concat(event_parts, "\n")
  else
    event_summary = "Routine operations. No major incidents to report."
  end

  -- Build context
  local context_parts = {}

  table.insert(context_parts, string.format("DIRECTOR'S LOG - GENERATION %d", generation))
  table.insert(context_parts, string.format("Stardate: %d", year))
  table.insert(context_parts, "")

  table.insert(context_parts, "STATUS SUMMARY:")
  if game_state.public_support then
    table.insert(context_parts, string.format("- Public Support: %d%%", game_state.public_support))
  end
  if game_state.funding then
    table.insert(context_parts, string.format("- Funding: %d%%", game_state.funding))
  end
  if game_state.knowledge_base then
    table.insert(context_parts, string.format("- Knowledge Base: %d%%", game_state.knowledge_base))
  end
  table.insert(context_parts, "")

  table.insert(context_parts, "KEY EVENTS THIS GENERATION:")
  table.insert(context_parts, event_summary)
  table.insert(context_parts, "")

  -- Civilization status
  if game_state.civilizations then
    local contacted = 0
    local discovered = 0
    local extinct = 0

    for _, civ in pairs(game_state.civilizations) do
      discovered = discovered + 1
      if civ.contacted then
        contacted = contacted + 1
      end
      if civ.extinct then
        extinct = extinct + 1
      end
    end

    table.insert(context_parts, string.format("CIVILIZATION STATUS:"))
    table.insert(context_parts, string.format("- Total Discovered: %d", discovered))
    table.insert(context_parts, string.format("- Successfully Contacted: %d", contacted))
    if extinct > 0 then
      table.insert(context_parts, string.format("- Extinct Civilizations Found: %d", extinct))
    end
    table.insert(context_parts, "")
  end

  -- Threat status
  if game_state.pending_attacks and #game_state.pending_attacks > 0 then
    table.insert(context_parts, string.format("⚠️  THREAT ALERT: %d hostile fleets detected inbound", #game_state.pending_attacks))
    table.insert(context_parts, "")
  end

  local context = table.concat(context_parts, "\n")

  -- Build generation prompt
  local system_prompt = [[You are writing the Director's Log for the SETI program - a summary of events this generation.

The log should:
- Capture the major events and discoveries
- Reflect on the significance of findings
- Note any concerns or achievements
- Be written in a professional but reflective tone
- Be 2-3 paragraphs total

Write as if you are the Director of this generations-long project, recording history for future generations.]]

  local generation_prompt = string.format([[
Write the Director's Log entry for this generation:

%s

Write 2-3 paragraphs that capture:
1. The major events and their significance
2. Reflections on our progress toward contact
3. Any concerns or achievements worth noting
4. A forward-looking statement about the next generation

Tone should be professional, reflective, and appropriate for an official log entry.]], context)

  -- Generate log entry
  local log_entry, err = llm.generate(generation_prompt, system_prompt)

  if err then
    -- Fallback log
    log_entry = M.fallback_log(generation, year, events, game_state)
  end

  return {
    generation = generation,
    year = year,
    log_entry = log_entry,
    timestamp = os.time()
  }
end

-- Fallback log if LLM fails
function M.fallback_log(generation, year, events, game_state)
  local parts = {}

  table.insert(parts, string.format("Director's Log - Generation %d", generation))
  table.insert(parts, string.format("Stardate: %d\n", year))

  -- First paragraph: Events
  if #events > 0 then
    table.insert(parts, "This generation has been marked by significant developments.")
    for _, event in ipairs(events) do
      table.insert(parts, string.format("We observed %s.", event.description or event.type))
    end
  else
    table.insert(parts, "This generation has proceeded according to expectations. Our instruments continue their vigil, scanning the cosmos for signs of intelligence.")
  end

  -- Second paragraph: Status and reflection
  table.insert(parts, "")

  local support = game_state.public_support or 50
  if support > 70 then
    table.insert(parts, "Public support remains strong, allowing us to maintain our operations at full capacity. The funding situation is stable, and our research continues unimpeded.")
  elseif support > 40 then
    table.insert(parts, "Public support has shown some fluctuations, but remains adequate for our needs. We continue to advocate for the importance of our mission to Earth's leadership.")
  else
    table.insert(parts, "We face challenges in maintaining public and political support. The long timescales of interstellar communication test humanity's patience, yet we persist in our vigil.")
  end

  -- Third paragraph: Forward-looking
  table.insert(parts, "")

  local contacted = 0
  if game_state.civilizations then
    for _, civ in pairs(game_state.civilizations) do
      if civ.contacted then
        contacted = contacted + 1
      end
    end
  end

  if contacted >= 3 then
    table.insert(parts, "We have achieved what once seemed impossible: confirmed contact with multiple alien civilizations. The implications will occupy philosophers and scientists for generations to come.")
  elseif contacted > 0 then
    table.insert(parts, string.format("We have established contact with %d civilization(s). Each exchange of messages brings us closer to understanding our place in the cosmos.", contacted))
  else
    table.insert(parts, "We continue to search. The silence of the cosmos is profound, but we remain committed to our mission. Somewhere out there, others must be listening.")
  end

  return table.concat(parts, "\n")
end

-- HTTP request handler
function M.handle_request(req)
  local path = req:path()
  local method = req:method()

  if path == "/director_log/narrate" and method == "POST" then
    local body = json.decode(req:read_body())
    local result = M.narrate(body)
    return {status = 200, body = json.encode(result)}
  end

  return {status = 404, body = json.encode({error = "Not found"})}
end

-- Spawn function for process entry
function M.spawn()
  process_id = "director_log-" .. os.time()

  while true do
    local msg = process.receive()

    if msg.type == "http_request" then
      local result = M.handle_request(msg.data)
      process.send(msg.reply_to, {
        type = "http_response",
        data = result
      })
    end
  end
end

return M
