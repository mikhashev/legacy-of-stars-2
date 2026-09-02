# AI in Legacy of Stars

## Principle: offline first

The game is complete without any language model. Every piece of generated text has a written
version that ships with the game:

| Content | Offline source | With an LLM |
|---|---|---|
| Alien replies (LB / LR / LBA, per civilization type) | `data/templates/alien_replies.json` | Generated from the strategy prompt and Earth's tech context |
| Swan songs (5 categories) | `data/templates/swan_songs.json` | Generated at discovery time |
| WOW! Signal response (Gen 144) and the 1977 reply | `data/templates/wow_responses.json` | Generated |
| Mirror civilization and Genesis messages | `data/templates/special_messages.json` | Written only |
| Strategic Advisor briefing | Rule-based analyst in `src/ai_strategic_advisor.py` | Generated from the same context |

The LLM never replaces game logic; it only rewrites flavour text. If a request fails, times out or
returns nothing, the written version is used and the player never sees an error message.

## Enabling an LLM

1. Copy `.env.example` to `.env` (optional) or export the variables.
2. Pick a provider alias from `data/llm_providers.json` with `AI_PROVIDER=<alias>`:
   - `ollama_local` (default): run Ollama on `http://127.0.0.1:11434` with the configured model.
   - `lm_studio`: OpenAI-compatible local server on port 1234.
   - `claude_haiku` / `claude_sonnet` / `claude_opus`: set `ANTHROPIC_API_KEY`.
   - `openai_gpt`: set `OPENAI_API_KEY`.
3. `LOS_OFFLINE=1` disables the LLM entirely (the test suite sets this).

At start-up the game probes the provider once (2 s timeout). Each request has a 20 s timeout and
two consecutive failures switch the LLM off for the rest of the session.

## Adding content

Template banks are plain JSON lists of strings with `{placeholders}`. Add variants to any list; the
game picks one at random. Unknown placeholders are left visible so mistakes are easy to spot
(`tests/test_content.py` checks every template renders without them).

## Ideas not pursued

Image, audio and video generation were considered (star portraits, signal audio, fleet animations)
and deliberately left out of the console game. They belong to a future graphical front-end, where
the engine's event stream (`GameEvent`) already provides the hooks such content would need.
