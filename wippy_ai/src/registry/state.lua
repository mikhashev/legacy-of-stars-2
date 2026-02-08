-- Registry State Management Module
-- Manages persistent state for AI learning and self-modification

local registry = require("registry")

local M = {}

-- Registry key prefixes
local KEYS = {
  ADVISOR = "game.advisor",
  CIV_RESPONSE = "game.civ_response",
  DIRECTOR_LOG = "game.director_log",
  LEARNING = "game.learning"
}

-- Default prompts
local DEFAULT_PROMPTS = {
  advisor_system = [[You are Earth's Strategic AI Advisor for SETI operations in a Dark Forest universe.

Your role:
- Analyze threats and opportunities
- Identify suspicious patterns
- Recommend specific actions
- Forecast long-term consequences

Remember:
- Dark Forest theory: Silence may indicate hostility (LA strategy)
- Not all civilizations are friendly (LA/LBA exist)
- Light-speed delays mean attacks take generations to arrive
- Resource management is critical (AP, support, funding)

Be concise, actionable, and strategic. Format your response with clear sections.]],

  civ_response = [[You are generating a response from an alien civilization in a Dark Forest universe.

Consider:
- Their civilization type (L, LB, LR, LA, LBA)
- How long they've known about us (light-speed delay)
- Their technological level relative to ours
- The existential risks they face

Generate a response that feels authentic to their psychology and situation.]],

  director_log = [[You are writing the Director's Log for the SETI program - a summary of events this generation.

The log should:
- Capture the major events and discoveries
- Reflect on the significance of findings
- Note any concerns or achievements
- Be written in a professional but reflective tone

Write 2-3 paragraphs that summarize the generation.]]
}

-- Initialize registry with default values
function M.init()
  -- Advisor prompts
  registry.set(KEYS.ADVISOR .. ".prompts.system", DEFAULT_PROMPTS.advisor_system)

  -- Advisor strategy weights
  registry.set(KEYS.ADVISOR .. ".strategy.aggression", 0.5)
  registry.set(KEYS.ADVISOR .. ".strategy.caution", 0.5)
  registry.set(KEYS.ADVISOR .. ".strategy.diplomacy", 0.5)

  -- Advisor learning history
  registry.set(KEYS.ADVISOR .. ".learning.outcomes", {})
  registry.set(KEYS.ADVISOR .. ".learning.success_count", 0)
  registry.set(KEYS.ADVISOR .. ".learning.failure_count", 0)

  -- Civilization response prompts
  registry.set(KEYS.CIV_RESPONSE .. ".prompts.default", DEFAULT_PROMPTS.civ_response)

  -- Director log prompts
  registry.set(KEYS.DIRECTOR_LOG .. ".prompts.default", DEFAULT_PROMPTS.director_log)

  -- Global learning state
  registry.set(KEYS.LEARNING .. ".total_generations", 0)
  registry.set(KEYS.LEARNING .. ".contacts_made", 0)
  registry.set(KEYS.LEARNING .. ".attacks_survived", 0)
  registry.set(KEYS.LEARNING .. ".civilizations_discovered", 0)
end

-- Get a value from registry
function M.get(key)
  local value = registry.get(key)
  return value
end

-- Set a value in registry
function M.set(key, value)
  registry.set(key, value)
  return true
end

-- Update advisor strategy based on outcome
function M.learn_advisor_outcome(outcome)
  local outcomes = registry.get(KEYS.ADVISOR .. ".learning.outcomes") or {}
  table.insert(outcomes, {
    generation = outcome.generation,
    type = outcome.type,
    success = outcome.success,
    aggression_level = outcome.aggression_level or 0.5,
    timestamp = os.time()
  })
  registry.set(KEYS.ADVISOR .. ".learning.outcomes", outcomes)

  -- Update counters
  if outcome.success then
    local count = registry.get(KEYS.ADVISOR .. ".learning.success_count") or 0
    registry.set(KEYS.ADVISOR .. ".learning.success_count", count + 1)
  else
    local count = registry.get(KEYS.ADVISOR .. ".learning.failure_count") or 0
    registry.set(KEYS.ADVISOR .. ".learning.failure_count", count + 1)
  end

  -- Simple learning: adjust aggression based on attack outcomes
  if outcome.type == "attack" then
    local current = registry.get(KEYS.ADVISOR .. ".strategy.aggression") or 0.5
    if outcome.success then
      -- If defense worked, increase aggression (be more proactive)
      registry.set(KEYS.ADVISOR .. ".strategy.aggression", math.min(1.0, current + 0.05))
    else
      -- If defense failed, increase caution (decrease aggression)
      registry.set(KEYS.ADVISOR .. ".strategy.aggression", math.max(0.0, current - 0.1))
    end
  end

  -- Update caution based on threat level
  if outcome.threat_level then
    local caution = registry.get(KEYS.ADVISOR .. ".strategy.caution") or 0.5
    -- Higher threat = higher caution
    local target_caution = math.min(1.0, outcome.threat_level)
    registry.set(KEYS.ADVISOR .. ".strategy.caution", (caution + target_caution) / 2)
  end
end

-- Get advisor's current strategy
function M.get_advisor_strategy()
  return {
    aggression = registry.get(KEYS.ADVISOR .. ".strategy.aggression") or 0.5,
    caution = registry.get(KEYS.ADVISOR .. ".strategy.caution") or 0.5,
    diplomacy = registry.get(KEYS.ADVISOR .. ".strategy.diplomacy") or 0.5
  }
end

-- Get advisor's system prompt
function M.get_advisor_prompt()
  return registry.get(KEYS.ADVISOR .. ".prompts.system") or DEFAULT_PROMPTS.advisor_system
end

-- Update advisor's system prompt (self-modification)
function M.update_advisor_prompt(new_prompt)
  registry.set(KEYS.ADVISOR .. ".prompts.system", new_prompt)
  return true
end

-- Get learning statistics
function M.get_learning_stats()
  return {
    outcomes = registry.get(KEYS.ADVISOR .. ".learning.outcomes") or {},
    success_count = registry.get(KEYS.ADVISOR .. ".learning.success_count") or 0,
    failure_count = registry.get(KEYS.ADVISOR .. ".learning.failure_count") or 0,
    total_generations = registry.get(KEYS.LEARNING .. ".total_generations") or 0,
    contacts_made = registry.get(KEYS.LEARNING .. ".contacts_made") or 0,
    attacks_survived = registry.get(KEYS.LEARNING .. ".attacks_survived") or 0
  }
end

-- Update global learning state
function M.update_global_stat(stat, value)
  local key = KEYS.LEARNING .. "." .. stat
  local current = registry.get(key) or 0
  registry.set(key, current + (value or 1))
end

-- Get all advisor learning outcomes
function M.get_advisor_outcomes()
  return registry.get(KEYS.ADVISOR .. ".learning.outcomes") or {}
end

-- HTTP endpoint handlers
function M.handle_http_request(req)
  local path = req:path()

  if path == "/registry/update" then
    -- Handle registry update
    local body = json.decode(req:read_body())
    if body.key and body.value ~= nil then
      M.set(body.key, body.value)
      return {status = 200, body = json.encode({success = true})}
    end
    return {status = 400, body = json.encode({error = "Missing key or value"})}

  elseif path == "/registry/get" then
    -- Handle registry get
    local query = req:query()
    local key = query.key
    if key then
      local value = M.get(key)
      return {status = 200, body = json.encode({key = key, value = value})}
    end
    return {status = 400, body = json.encode({error = "Missing key parameter"})}
  end

  return {status = 404, body = json.encode({error = "Not found"})}
end

-- Export for use in HTTP endpoints
return M
