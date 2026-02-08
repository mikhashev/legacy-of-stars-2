-- Wippy Documentation API Client Module
-- Fetches and searches Wippy documentation via llms.txt API

local http = require("http")
local json = require("json")

local M = {}

local base_url = "https://home.wj.wippy.ai/llm"

-- Helper function to encode URL parameters
local function urlencode(str)
  return (str:gsub("[^%w _~%-]", function(c)
    return ("%%%02X"):format(c:byte())
  end):gsub(" ", "+"))
end

-- Search Wippy documentation for relevant content
-- Returns: table of search results with chunk IDs
function M.search(query)
  local url = base_url .. "/search?q=" .. urlencode(query)

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Search failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Search returned status " .. resp.status
  end

  -- Try to decode as JSON first
  local success, results = pcall(json.decode, resp.body)
  if success then
    return results, nil
  end

  -- Fallback: parse as plain text if not JSON
  -- The search endpoint might return plain text
  return {results = resp.body}, nil
end

-- Get full content of a documentation page by path
-- path: e.g., "lua/core/process", "concepts/workflows"
function M.get_page(path, language)
  language = language or "en"
  local url = base_url .. "/path/" .. language .. "/" .. path

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get page failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get page returned status " .. resp.status
  end

  local success, result = pcall(json.decode, resp.body)
  if success then
    return result, nil
  end

  return resp.body, nil
end

-- Get summary of a documentation page
function M.get_summary(path, language)
  language = language or "en"
  local url = base_url .. "/summary/" .. language .. "/" .. path

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get summary failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get summary returned status " .. resp.status
  end

  local success, result = pcall(json.decode, resp.body)
  if success then
    return result, nil
  end

  return resp.body, nil
end

-- Get chunk by ID (from search results)
function M.get_chunk(chunk_id)
  local url = base_url .. "/chunk/" .. chunk_id

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get chunk failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get chunk returned status " .. resp.status
  end

  local success, chunk = pcall(json.decode, resp.body)
  if success then
    return chunk.content or chunk, nil
  end

  return resp.body, nil
end

-- Get related content for a chunk
function M.get_related(chunk_id)
  local url = base_url .. "/related/" .. chunk_id

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get related failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get related returned status " .. resp.status
  end

  local success, result = pcall(json.decode, resp.body)
  if success then
    return result, nil
  end

  return resp.body, nil
end

-- Batch fetch multiple pages
function M.get_context(paths)
  local paths_str = table.concat(paths, ",")
  local url = base_url .. "/context?paths=" .. paths_str

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get context failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get context returned status " .. resp.status
  end

  local success, result = pcall(json.decode, resp.body)
  if success then
    return result, nil
  end

  return resp.body, nil
end

-- Get table of contents
function M.get_toc()
  local url = base_url .. "/toc"

  local resp, err = http.get(url, {
    headers = {["Accept"] = "application/json"}
  })

  if err then
    return nil, "Get TOC failed: " .. tostring(err)
  end

  if resp.status ~= 200 then
    return nil, "Get TOC returned status " .. resp.status
  end

  local success, toc = pcall(json.decode, resp.body)
  if success then
    return toc, nil
  end

  return resp.body, nil
end

-- Convenience function: search and fetch first result
function M.search_and_fetch(query, max_results)
  max_results = max_results or 1

  local results, err = M.search(query)
  if err then
    return nil, err
  end

  -- Handle different response formats
  local chunks = {}
  if type(results) == "table" then
    if results.results then
      chunks = results.results
    elseif results[1] and results[1].id then
      chunks = results
    end
  end

  if #chunks == 0 then
    return nil, "No results found for query: " .. query
  end

  -- Fetch first few chunks
  local contents = {}
  for i = 1, math.min(max_results, #chunks) do
    local content, err = M.get_chunk(chunks[i].id)
    if content and not err then
      table.insert(contents, {
        id = chunks[i].id,
        path = chunks[i].path or "",
        content = content
      })
    end
  end

  return contents, nil
end

-- Map game concepts to Wippy documentation topics
local concept_mappings = {
  ["civilization_stability"] = {"concepts/process-model", "concepts/supervision", "lua/core/process"},
  ["self_modification"] = {"lua/dynamic/eval", "lua/core/registry", "concepts/registry"},
  ["communication"] = {"lua/http/http", "lua/http/client", "lua/core/channel"},
  ["knowledge_preservation"] = {"lua/storage/store", "lua/storage/sql", "lua/storage/filesystem"},
  ["resilience"] = {"concepts/compute-units", "lua/core/errors", "guides/supervision"},
  ["security"] = {"lua/security/security", "lua/security/crypto", "lua/security/hash"},
  ["workflow"] = {"concepts/workflows", "temporal/workflows", "temporal/activities"}
}

-- Get relevant documentation for a game concept
function M.get_for_concept(concept)
  local topics = concept_mappings[concept]
  if not topics then
    return nil, "Unknown concept: " .. tostring(concept)
  end

  return M.get_context(topics)
end

return M
