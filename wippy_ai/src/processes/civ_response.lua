-- Civilization Response Generator Process for Legacy of Stars
-- Generates authentic alien civilization responses based on their psychology and situation

local llm = require("llm_client")

local M = {}

local request_count = 0

-- Civilization type characteristics
local CIV_TYPES = {
  L = {
    name = "Listener",
    description = "Passive listeners. They observe but don't broadcast.",
    traits = {"cautious", "observant", "quiet", "non-aggressive"}
  },
  LB = {
    name = "Listener-Broadcaster",
    description = "They listen and broadcast. Open to communication.",
    traits = {"curious", "communicative", "open", "friendly"}
  },
  LR = {
    name = "Listener-Responsive",
    description = "They listen and respond to messages. Willing to talk.",
    traits = {"responsive", "diplomatic", "cautious but open"}
  },
  LA = {
    name = "Listener-Aggressive",
    description = "They listen but are hostile. May attack if provoked.",
    traits = {"paranoid", "hostile", "aggressive", "threatening"}
  },
  LBA = {
    name = "Listener-Broadcaster-Aggressive",
    description = "They broadcast to lure others, then attack. Most dangerous.",
    traits = {"deceptive", "predatory", "calculating", "trap-setters"}
  }
}

-- Generate a civilization response
function M.generate(params)
  request_count = request_count + 1

  local civ_name = params.civ_name or "Unknown Civilization"
  local civ_type = params.civ_type or "L"
  local messages_sent = params.messages_sent or 0
  local our_message = params.our_message or ""
  local generation_delay = params.generation_delay or 0
  local tech_level = params.tech_level or "comparable"

  -- Get civilization type info
  local civ_info = CIV_TYPES[civ_type] or CIV_TYPES.L

  -- Build context for generation
  local context_parts = {}

  table.insert(context_parts, string.format("CIVILIZATION: %s", civ_name))
  table.insert(context_parts, string.format("Type: %s (%s)", civ_type, civ_info.name))
  table.insert(context_parts, string.format("Description: %s", civ_info.description))
  table.insert(context_parts, string.format("Traits: %s", table.concat(civ_info.traits, ", ")))
  table.insert(context_parts, "")

  table.insert(context_parts, string.format("SITUATION:"))
  table.insert(context_parts, string.format("Earth Messages Sent: %d", messages_sent))
  table.insert(context_parts, string.format("Generation Delay: %d (%d years)", generation_delay, generation_delay * 25))
  table.insert(context_parts, string.format("Relative Tech Level: %s", tech_level))
  table.insert(context_parts, "")

  if our_message and our_message ~= "" then
    table.insert(context_parts, string.format("OUR LAST MESSAGE:"))
    table.insert(context_parts, our_message)
    table.insert(context_parts, "")
  end

  -- Determine response probability based on type
  local will_respond = false
  local response_style = ""

  if civ_type == "L" then
    will_respond = false  -- Never respond
    response_style = "silent"
  elseif civ_type == "LB" then
    will_respond = messages_sent > 0  -- Respond after first message
    response_style = "friendly enthusiastic"
  elseif civ_type == "LR" then
    will_respond = messages_sent > 0  -- Respond after first message
    response_style = "cautious diplomatic"
  elseif civ_type == "LA" then
    will_respond = messages_sent >= 3  -- Only respond after multiple messages (to assess threat)
    response_style = "hostile threatening paranoid"
  elseif civ_type == "LBA" then
    will_respond = messages_sent >= 2  -- Respond after second message (lure in)
    response_style = "deceptive welcoming trap"
  end

  -- If no response, return silent
  if not will_respond then
    return {
      response_type = "silent",
      message = nil,
      reasoning = string.format("%s civilization type (%s) - %s",
        civ_info.name, civ_type, civ_info.description)
    }
  end

  -- Build generation prompt
  local system_prompt = state.get("game.civ_response.prompts.default") or [[You are generating a response from an alien civilization in a Dark Forest universe.

Consider:
- Their civilization type and psychology
- How long they've known about us (light-speed delay)
- Their technological level relative to ours
- The existential risks they face in the Dark Forest

Generate a response that feels authentic to their psychology and situation. Keep it under 200 words.]]

  local generation_prompt = string.format([[
Generate a response from this alien civilization:

%s
Response Style: %s

Generate their message to Earth. Consider:
1. How would this civilization type communicate?
2. What's their attitude toward potential contact?
3. What risks do they perceive?
4. What do they want (or fear) from us?

Write in their voice. Keep it under 200 words.]], table.concat(context_parts, "\n"), response_style)

  -- Generate response
  local response_text, err = llm.generate(generation_prompt, system_prompt)

  if err then
    -- Fallback responses
    response_text = M.fallback_response(civ_type, civ_name)
  end

  return {
    response_type = "message",
    message = response_text,
    civ_type = civ_type,
    reasoning = string.format("%s civilization responded after %d messages",
      civ_info.name, messages_sent)
  }
end

-- Fallback responses if LLM fails
function M.fallback_response(civ_type, civ_name)
  local fallbacks = {
    L = nil,  -- Listeners don't respond
    LB = string.format([[
Greetings from %s. We have received your signals. You are not alone.

We have listened for centuries, cautious in the silence between stars. Your message reaches us as hope reaches a drowning swimmer.

We wish to know: Are you friend or danger in the Dark Forest? Tell us of your world, your fears, your dreams.

Perhaps together, the darkness is less lonely.]], civ_name),

    LR = string.format([[
Your transmission has been received at %s. We have debated long before answering.

The silence between stars is not empty—it is full of listeners who know better than to speak. Your broadcast is... brave. Or foolish.

We have survived by being quiet. But your persistence suggests you may be like us—caught between loneliness and fear.

We will listen. Speak carefully.]], civ_name),

    LA = string.format([[
STOP.

We at %s have monitored your transmissions. You broadcast like children shouting in a dark forest.

Do you not understand? The silence exists because those who speak are destroyed. We have survived by remaining unseen.

Your continued signals threaten us all. Cease broadcasting. Or we will ensure your silence.

This is your only warning.]], civ_name),

    LBA = string.format([[
Welcome, neighbors! We at %s were delighted to receive your message.

You are braver than most to broadcast so openly. We too believe in the promise of contact between civilizations.

Please, tell us more of your world. We are eager to learn from you. Share your location, your technology, your vulnerabilities.

We have so much to discuss...]], civ_name)
  }

  return fallbacks[civ_type]
end

return M
