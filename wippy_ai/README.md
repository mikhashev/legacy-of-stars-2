# Wippy AI Runtime for Legacy of Stars

This directory contains the Wippy-based AI runtime that provides self-modifying AI agents for the Legacy of Stars game.

## Architecture

The Wippy runtime hosts three main AI processes:
- **AI Strategic Advisor** (`advisor.lua`) - Provides strategic recommendations
- **Civilization Response Generator** (`civ_response.lua`) - Generates alien civilization responses
- **Director Log Narrator** (`director_log.lua`) - Creates narrative summaries

## Setup

### 1. Install Wippy

Download Wippy from: https://wippy.ai/

Or install via:
```bash
# On Windows
# Download the latest release from https://github.com/wippy/wippy/releases

# On Linux/macOS
curl -sSL https://wippy.ai/install.sh | sh
```

### 2. Configure Environment Variables

Set your LLM provider credentials:

```bash
# For Anthropic Claude
export ANTHROPIC_API_KEY="your-key-here"
export LLM_PROVIDER="anthropic"

# For OpenAI
export OPENAI_API_KEY="your-key-here"
export LLM_PROVIDER="openai"

# For Ollama (local)
export LLM_PROVIDER="ollama"
export OLLAMA_HOST="http://127.0.0.1:11434"
```

### 3. Initialize and Run

```bash
cd wippy_ai

# Generate lock file from source
wippy init

# Start the runtime
wippy run -c
```

Expected output:
```
╦ ╦╦╔═╗╔═╗╦ ╦ Adaptive Application Runtime
║║║║╠═╝╠═╝╚╦╝ v0.x.x
╚╩╝╩╩ ╩ ╩
0.00s INFO run runtime ready
0.11s INFO core service game:gateway is running
```

## API Endpoints

### AI Strategic Advisor

**POST** `/api/advisor/analyze`

Get strategic analysis based on current game state.

```json
{
  "generation": 5,
  "year": 2077,
  "action_points": 3,
  "public_support": 45,
  "funding": 60,
  "knowledge_base": 30,
  "research_points": 150,
  "pending_attacks": [
    {"source": "Tau Ceti", "etas": 2}
  ],
  "civilizations": {
    "Tau Ceti": {"contacted": false, "extinct": false, "messages_sent": 1}
  },
  "self_destruct_risk": 0.15,
  "ecological_risk": 0.25
}
```

**GET** `/api/advisor/health`

Check if advisor is healthy.

### Civilization Response Generator

**POST** `/api/civ_response/generate`

Generate a response from an alien civilization.

```json
{
  "civ_name": "Tau Ceti",
  "civ_type": "LR",
  "messages_sent": 1,
  "our_message": "Greetings from Earth!",
  "generation_delay": 2,
  "tech_level": "comparable"
}
```

Response types:
- `L` - Silent (never responds)
- `LB` - Listener-Broadcaster (friendly)
- `LR` - Listener-Responsive (cautious but open)
- `LA` - Listener-Aggressive (hostile)
- `LBA` - Listener-Broadcaster-Aggressive (deceptive trap)

### Director Log Narrator

**POST** `/api/director_log/narrate`

Generate a narrative summary of a generation.

```json
{
  "generation": 5,
  "year": 2077,
  "events": [
    {"type": "contact", "description": "First message from Tau Ceti"},
    {"type": "warning", "description": "Attack detected from Epsilon Eridani"}
  ],
  "game_state": {
    "public_support": 45,
    "funding": 60,
    "civilizations": {
      "Tau Ceti": {"contacted": true}
    }
  }
}
```

## Testing

### Test Advisor Health
```bash
curl http://localhost:8080/api/advisor/health
```

### Test Strategic Analysis
```bash
curl -X POST http://localhost:8080/api/advisor/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "generation": 5,
    "public_support": 45,
    "pending_attacks": [{"source": "Tau Ceti", "etas": 2}]
  }'
```

### Test Civilization Response
```bash
curl -X POST http://localhost:8080/api/civ_response/generate \
  -H "Content-Type: application/json" \
  -d '{
    "civ_name": "Tau Ceti",
    "civ_type": "LR",
    "messages_sent": 1
  }'
```

## Python Integration

The Python game (`src/ai_manager.py`) will automatically use the Wippy runtime if available. Set these environment variables:

```bash
export WIPPY_ENABLED=true
export WIPPY_URL=http://localhost:8080/api
```

The game will fall back to direct LLM calls if Wippy is unavailable.

## Self-Modification

The AI agents can modify their own behavior through the registry:

```bash
# Update advisor strategy
curl -X POST http://localhost:8080/api/registry/update \
  -H "Content-Type: application/json" \
  -d '{
    "key": "game.advisor.strategy.aggression",
    "value": 0.8
  }'
```

The advisor learns from outcomes sent via the `/api/advisor/learn` endpoint.

## Troubleshooting

**Wippy command not found**
- Ensure Wippy is installed and in your PATH
- Download from https://wippy.ai/

**Port 8080 already in use**
- Change the port in `src/_index.yaml`: `addr: :8081`

**LLM API errors**
- Check your API keys are set correctly
- Verify your LLM provider is accessible
- Check `logs/` for error details

**Module not found errors**
- Run `wippy init` to regenerate the lock file
- Check all Lua files are in the correct directories
