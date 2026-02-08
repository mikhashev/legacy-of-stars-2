-- AI Strategic Advisor Process for Legacy of Stars
-- Provides context-aware strategic recommendations using AI
-- Self-modifying: adjusts strategy based on game outcomes

local http = require("http")
local json = require("json")
local llm = require("llm_client")
local docs = require("wippy_docs")
local state = require("registry_state")

local M = {}

-- Process ID for tracking
local process_id = nil
local request_count = 0

-- Build game context from Python request
local function build_context(game_state)
  local context_parts = {}

  -- Basic state
  table.insert(context_parts, "CURRENT STATE:")
  table.insert(context_parts, string.format("Generation: %d", game_state.generation or 1))
  table.insert(context_parts, string.format("Year: %d", game_state.year or 1977))

  -- Resources
  if game_state.action_points then
    table.insert(context_parts, string.format("Action Points: %d/%d",
      game_state.action_points, game_state.max_action_points or game_state.action_points))
  end
  if game_state.public_support then
    table.insert(context_parts, string.format("Public Support: %d%%", game_state.public_support))
  end
  if game_state.funding then
    table.insert(context_parts, string.format("Funding: %d%%", game_state.funding))
  end
  if game_state.knowledge_base then
    table.insert(context_parts, string.format("Knowledge Base: %d%%", game_state.knowledge_base))
  end
  if game_state.research_points then
    table.insert(context_parts, string.format("Research Points: %d", game_state.research_points))
  end
  table.insert(context_parts, "")

  -- Active threats
  if game_state.pending_attacks and #game_state.pending_attacks > 0 then
    table.insert(context_parts, string.format("ACTIVE THREATS: %d", #game_state.pending_attacks))
    for _, threat in ipairs(game_state.pending_attacks) do
      table.insert(context_parts, string.format("  - %s: %d generations away",
        threat.source or "Unknown", threat.etas or 0))
    end
    table.insert(context_parts, "")
  else
    table.insert(context_parts, "ACTIVE THREATS: None")
    table.insert(context_parts, "")
  end

  -- Known civilizations
  if game_state.civilizations then
    table.insert(context_parts, "KNOWN CIVILIZATIONS:")

    local contacted = {}
    local silent = {}
    local extinct = {}

    for name, civ in pairs(game_state.civilizations) do
      if civ.extinct then
        table.insert(extinct, name)
      elseif civ.contacted then
        table.insert(contacted, name)
      elseif civ.messages_sent and civ.messages_sent > 0 then
        table.insert(silent, {name = name, count = civ.messages_sent})
      end
    end

    table.insert(context_parts, string.format("  Contacted (friendly): %d", #contacted))
    if #contacted > 0 then
      table.insert(context_parts, "    " .. table.concat(contacted, ", "))
    end

    if #silent > 0 then
      table.insert(context_parts, string.format("  Silent (messaged but no response): %d", #silent))
      for _, s in ipairs(silent) do
        table.insert(context_parts, string.format("    %s (%d messages sent, 0 received)", s.name, s.count))
      end
    end

    if #extinct > 0 then
      table.insert(context_parts, string.format("  Extinct: %d", #extinct))
      table.insert(context_parts, "    " .. table.concat(extinct, ", "))
    end

    table.insert(context_parts, "")
  end

  -- Existential risks
  table.insert(context_parts, "EXISTENTIAL RISKS:")
  if game_state.self_destruct_risk then
    table.insert(context_parts, string.format("  Self-Destruct: %.1f%%", game_state.self_destruct_risk * 100))
  end
  if game_state.ecological_risk then
    table.insert(context_parts, string.format("  Ecological: %.1f%%", game_state.ecological_risk * 100))
  end
  table.insert(context_parts, "")

  -- Current strategy
  local strategy = state.get_advisor_strategy()
  table.insert(context_parts, string.format("CURRENT STRATEGY:"))
  table.insert(context_parts, string.format("  Aggression: %.2f", strategy.aggression))
  table.insert(context_parts, string.format("  Caution: %.2f", strategy.caution))
  table.insert(context_parts, "")

  -- Victory progress
  local contacted_count = 0
  if game_state.civilizations then
    for _, civ in pairs(game_state.civilizations) do
      if civ.contacted then
        contacted_count = contacted_count + 1
      end
    end
  end
  table.insert(context_parts, string.format("VICTORY PROGRESS: %d/3 contacts needed", contacted_count))

  return table.concat(context_parts, "\n")
end

-- Analyze game state and provide recommendations
function M.analyze(game_state)
  request_count = request_count + 1

  -- Get current prompts and strategy from registry
  local system_prompt = state.get_advisor_prompt()
  local strategy = state.get_advisor_strategy()

  -- Query Wippy docs for relevant concepts (if applicable)
  local docs_context = ""
  if game_state.has_threats or (game_state.self_destruct_risk and game_state.self_destruct_risk > 0.3) then
    local docs_result, err = docs.search_and_fetch("supervision fault tolerance resilience", 1)
    if docs_result and #docs_result > 0 then
      docs_context = "\n\n[TECHNICAL REFERENCE: " .. docs_result[1].path .. "]\n" ..
                    string.sub(docs_result[1].content, 1, 500) .. "..."
    end
  end

  -- Build comprehensive context
  local context = build_context(game_state)

  -- Create analysis prompt
  local analysis_prompt = string.format([[
Analyze the current game state and provide strategic recommendations:

%s

Current Strategy Settings:
- Aggression: %.2f (0 = pacifist, 1 = aggressive)
- Caution: %.2f (0 = bold, 1 = cautious)
%s

Provide:
1. THREAT ASSESSMENT (current danger level)
2. SUSPICIOUS PATTERNS (systems to avoid/watch)
3. RECOMMENDED ACTIONS (what to do this generation)
4. LONG-TERM STRATEGY (next 3-5 generations)
5. FORECAST (predicted outcomes)

Keep each section brief (2-3 sentences max). Be direct and actionable.]], context, strategy.aggression, strategy.caution, docs_context)

  -- Generate strategic analysis
  local response, err = llm.generate(analysis_prompt, system_prompt)

  if err then
    -- Fallback response if LLM fails
    response = M.fallback_analysis(game_state)
  end

  -- Format and return
  return {
    request_id = request_count,
    response = response,
    strategy_used = strategy,
    timestamp = os.time()
  }
end

-- Fallback analysis if LLM fails
function M.fallback_analysis(game_state)
  local parts = {}

  -- Threat assessment
  table.insert(parts, "\nTHREAT ASSESSMENT:")

  local threat_count = 0
  if game_state.pending_attacks then
    threat_count = #game_state.pending_attacks
  end

  if threat_count > 0 then
    table.insert(parts, string.format("⚠️  HIGH RISK - %d hostile fleet(s) incoming. Deploy defenses immediately.", threat_count))
  else
    table.insert(parts, "✓ No active threats detected. Situation stable.")
  end

  -- Resource status
  table.insert(parts, "\nRESOURCE STATUS:")

  if game_state.public_support and game_state.public_support < 30 then
    table.insert(parts, "❌ CRITICAL: Public support dangerously low. Conduct outreach NOW.")
  elseif game_state.public_support and game_state.public_support < 50 then
    table.insert(parts, "⚠️  WARNING: Public support declining. Consider outreach campaign.")
  else
    table.insert(parts, "✓ Public support adequate.")
  end

  if game_state.funding and game_state.funding < 30 then
    table.insert(parts, "❌ CRITICAL: Funding crisis. Boost support to restore funding.")
  elseif game_state.funding and game_state.funding < 50 then
    table.insert(parts, "⚠️  WARNING: Funding below optimal. Support restoration recommended.")
  end

  -- Recommended actions
  table.insert(parts, "\nRECOMMENDED ACTIONS:")

  if threat_count > 0 then
    table.insert(parts, "1. Deploy defensive measures against incoming threats")
  end

  if game_state.public_support and game_state.public_support < 50 then
    table.insert(parts, "2. Public Outreach Campaign to restore support")
  end

  local contacted_count = 0
  if game_state.civilizations then
    for _, civ in pairs(game_state.civilizations) do
      if civ.contacted then
        contacted_count = contacted_count + 1
      end
    end
  end

  if contacted_count < 3 then
    table.insert(parts, string.format("3. Continue contact efforts (%d/3 needed for victory)", contacted_count))
  end

  table.insert(parts, string.format("\nVICTORY PROGRESS: %d/3 contacts established", contacted_count))

  return table.concat(parts, "\n")
end

-- Learn from an outcome
function M.learn(outcome)
  state.learn_advisor_outcome(outcome)
  return {success = true, message = "Learning outcome recorded"}
end

-- Health check
function M.health()
  return {
    status = "healthy",
    process_id = process_id,
    request_count = request_count,
    strategy = state.get_advisor_strategy(),
    learning_stats = state.get_learning_stats()
  }
end

-- HTTP request handler
function M.handle_request(req)
  local path = req:path()
  local method = req:method()

  if path == "/advisor/analyze" and method == "POST" then
    local body = json.decode(req:read_body())
    local result = M.analyze(body)
    return {status = 200, body = json.encode(result)}

  elseif path == "/advisor/learn" and method == "POST" then
    local body = json.decode(req:read_body())
    local result = M.learn(body)
    return {status = 200, body = json.encode(result)}

  elseif path == "/advisor/health" and method == "GET" then
    local result = M.health()
    return {status = 200, body = json.encode(result)}
  end

  return {status = 404, body = json.encode({error = "Not found"})}
end

-- Spawn function for process entry
function M.spawn()
  process_id = "advisor-" .. os.time()

  -- Initialize state if not already done
  state.init()

  -- Main process loop
  while true do
    local msg = process.receive()

    if msg.type == "http_request" then
      local result = M.handle_request(msg.data)
      process.send(msg.reply_to, {
        type = "http_response",
        data = result
      })
    elseif msg.type == "analyze_request" then
      local result = M.analyze(msg.data)
      process.send(msg.reply_to, {
        type = "analyze_response",
        data = result
      })
    elseif msg.type == "registry_update" then
      -- Self-modify when registry changes
      -- Prompts will be reloaded on next analyze call
    end
  end
end

return M
