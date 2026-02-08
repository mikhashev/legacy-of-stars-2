-- LLM Client Module for Legacy of Stars AI
-- Supports Anthropic Claude, OpenAI, and Ollama APIs

local http = require("http")
local json = require("json")

local M = {}

-- Configuration (loaded from environment or defaults)
local config = {
  -- Default provider (can be "anthropic", "openai", "ollama")
  provider = os.getenv("LLM_PROVIDER") or "ollama",

  -- Anthropic configuration
  anthropic = {
    api_key = os.getenv("ANTHROPIC_API_KEY") or "",
    model = os.getenv("ANTHROPIC_MODEL") or "claude-3-haiku-20240307",
    base_url = "https://api.anthropic.com/v1"
  },

  -- OpenAI configuration
  openai = {
    api_key = os.getenv("OPENAI_API_KEY") or "",
    model = os.getenv("OPENAI_MODEL") or "gpt-3.5-turbo",
    base_url = os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
  },

  -- Ollama configuration
  ollama = {
    host = os.getenv("OLLAMA_HOST") or "http://127.0.0.1:11434",
    model = os.getenv("OLLAMA_MODEL") or "llama3.1:8b"
  }
}

-- Helper function to encode URL parameters
local function urlencode(str)
  return (str:gsub("[^%w _~%-]", function(c)
    return ("%%%02X"):format(c:byte())
  end):gsub(" ", "+"))
end

-- Call Anthropic Claude API
local function call_anthropic(prompt, system_prompt, max_tokens)
  local api_key = config.anthropic.api_key
  if not api_key or api_key == "" then
    return nil, "ANTHROPIC_API_KEY not set"
  end

  local url = config.anthropic.base_url .. "/messages"

  local payload = {
    model = config.anthropic.model,
    max_tokens = max_tokens or 1024,
    system = system_prompt or "You are a sci-fi game master.",
    messages = {
      {role = "user", content = prompt}
    }
  }

  local body = json.encode(payload)
  local headers = {
    ["x-api-key"] = api_key,
    ["anthropic-version"] = "2023-06-01",
    ["content-type"] = "application/json"
  }

  local resp, err = http.post(url, {
    body = body,
    headers = headers
  })

  if err then
    return nil, "Anthropic API error: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Anthropic API returned status " .. resp.status .. ": " .. resp.body
  end

  local result = json.decode(resp.body)
  return result.content[1].text, nil
end

-- Call OpenAI API
local function call_openai(prompt, system_prompt, max_tokens)
  local api_key = config.openai.api_key
  if not api_key or api_key == "" then
    return nil, "OPENAI_API_KEY not set"
  end

  local url = config.openai.base_url .. "/chat/completions"

  local payload = {
    model = config.openai.model,
    messages = {
      {role = "system", content = system_prompt or "You are a sci-fi game master."},
      {role = "user", content = prompt}
    },
    temperature = 0.7
  }

  local body = json.encode(payload)
  local headers = {
    ["Authorization"] = "Bearer " .. api_key,
    ["Content-Type"] = "application/json"
  }

  local resp, err = http.post(url, {
    body = body,
    headers = headers
  })

  if err then
    return nil, "OpenAI API error: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "OpenAI API returned status " .. resp.status .. ": " .. resp.body
  end

  local result = json.decode(resp.body)
  return result.choices[1].message.content, nil
end

-- Call Ollama API
local function call_ollama(prompt, system_prompt, max_tokens)
  local url = config.ollama.host .. "/api/generate"

  local payload = {
    model = config.ollama.model,
    prompt = prompt,
    system = system_prompt or "You are a sci-fi game master.",
    stream = false
  }

  local body = json.encode(payload)
  local headers = {
    ["Content-Type"] = "application/json"
  }

  local resp, err = http.post(url, {
    body = body,
    headers = headers
  })

  if err then
    return nil, "Ollama API error: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Ollama API returned status " .. resp.status .. ": " .. resp.body
  end

  local result = json.decode(resp.body)
  return result.response, nil
end

-- Main generate function
function M.generate(prompt, system_prompt, provider_override)
  provider_override = provider_override or config.provider

  if provider_override == "anthropic" then
    return call_anthropic(prompt, system_prompt)
  elseif provider_override == "openai" then
    return call_openai(prompt, system_prompt)
  elseif provider_override == "ollama" then
    return call_ollama(prompt, system_prompt)
  else
    return nil, "Unknown provider: " .. tostring(provider_override)
  end
end

-- Set provider
function M.set_provider(provider)
  config.provider = provider
end

-- Set API key for a provider
function M.set_api_key(provider, key)
  if config[provider] then
    config[provider].api_key = key
  end
end

-- Set model for a provider
function M.set_model(provider, model)
  if config[provider] then
    config[provider].model = model
  end
end

-- Get current configuration
function M.get_config()
  return config
end

return M
