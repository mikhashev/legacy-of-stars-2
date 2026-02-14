# AI Generative Content Roadmap for Real-Time Gameplay

## Overview

This document outlines the planned integration of AI-generated content (images, text, audio, video) for enhancing real-time gameplay in Legacy of Stars. Based on the Game Design Document and existing game mechanics, this roadmap defines priorities, implementation points, and technical architecture.

---

## Current AI Implementation (Text-Only)

| Feature | Status | File |
|---------|--------|------|
| AI Strategic Advisor | ✅ Complete | `src/ai_strategic_advisor.py` |
| Swan Song Messages | ✅ Complete | `src/swan_song_messages.py` |
| Civilization Responses | ✅ Complete | `wippy_ai/src/processes/civ_response.lua` |
| Director Log Narrator | ✅ Complete | `wippy_ai/src/processes/director_log.lua` |
| Wippy Adaptive Agents | 🔧 Config Fixes | `wippy_ai/` runtime |
| AI Manager (multi-provider) | ✅ Complete | `src/ai_manager.py` |

### Wippy Integration Status

**Python-side (Complete):**
- AIManager class with Wippy endpoint integration
- Fallback to direct LLM calls when Wippy unavailable
- Environment variables: `WIPPY_URL`, `WIPPY_ENABLED`
- Methods: `check_wippy_health()`, `wippy_civ_response()`, `wippy_director_log()`, `wippy_learn()`

**Wippy-side (In Progress):**
- Configuration fixes for handler types (`library.lua` → `function.lua`)
- Router configuration updates
- Test handler for verification (`test_handler.lua`)

**Supported Providers:** Ollama (local), Anthropic Claude, OpenAI, Wippy Runtime

---

## Priority 1: Image Generation

### Gameplay Integration Points

| Gameplay Moment | AI Content | Trigger | Impact |
|-----------------|------------|---------|--------|
| **Star System Discovery** | Unique planet/star visualization | First contact with system | Immersion, memorability |
| **Swan Song Discovery** | Artifact visualization (data crystal, ruin) | 30%+ knowledge discovery | Emotional weight |
| **WOW! Signal Detection** | Signal waveform visualization | Game start (Gen 1) | Historic authenticity |
| **Attack Fleet Warning** | Countdown imagery, fleet silhouette | Hostile civ detects Earth | Tension building |
| **Director Portrait** | AI-generated portrait per generation | Each new director | Character connection |
| **Philosophical Events** | Abstract imagery (Biology-Tech gap, etc.) | Event trigger | Thematic depth |
| **Victory/Defeat** | Cinematic still image | Game end | Closure |

### Implementation Files

- `src/philosophical_events.py` - 5 crisis events need visuals
- `src/wow_signal_event.py` - Opening scenario
- `src/attack_warning.py` - Defense countdown
- `src/swan_song_messages.py` - Extinct civ artifacts

### Image Generation APIs

| Provider | Use Case | Notes |
|----------|----------|-------|
| DALL-E 3 | High-quality concept art | API-based, cost per image |
| Stable Diffusion | Local generation | Free, requires GPU |
| Midjourney | Artistic style | Via Discord/API |

---

## Priority 2: Enhanced Text Generation

### Gameplay Integration Points

| Gameplay Moment | AI Content | Current State | Enhancement |
|-----------------|------------|---------------|-------------|
| **Philosophical Events** | Dynamic descriptions | Static text | AI variations based on game state |
| **Director Commentary** | Personality-driven text | Basic traits | AI-voiced reflections |
| **News Headlines** | Procedural generation | None | Era-appropriate news each generation |
| **Civilization Profiles** | Culture descriptions | None | AI-generated encyclopedic entries |
| **Victory Narratives** | Extended endings | Basic | Personalized legacy story |

### Implementation Files

- `src/ai_manager.py` - `generate_text()` method
- `wippy_ai/` - Adaptive response generation

### Text Generation Prompts

**Director Commentary Example:**
```
System: You are a SETI program director in {year} with traits {traits}.
Generate a brief reflection on the current state of the program.

Context: {game_state}

Output: 2-3 sentences reflecting the director's personality and concerns.
```

**News Headlines Example:**
```
System: Generate 3 news headlines from {year} related to SETI and space exploration.
Style: {era_appropriate_journalism}
Context: {recent_events}

Output: 3 headlines with brief 1-sentence summaries.
```

---

## Priority 3: Audio Generation

### Gameplay Integration Points

| Gameplay Moment | AI Content | Trigger | Implementation |
|-----------------|------------|---------|----------------|
| **Alien Signals** | Synthesized transmission sounds | Message received | Audio from signal patterns |
| **WOW! Signal** | Authentic 1972 audio recreation | Game start | Historic fidelity |
| **Swan Song "Voice"** | Distorted, haunting audio | Discovery | Emotional impact |
| **Ambient Soundscape** | Era-evolving background | Each generation | 1970s radio → 2500s digital |
| **AI Advisor Voice** | Spoken briefings | Advisor unlock | Accessibility |
| **Attack Warning Siren** | Tension audio | Hostile detection | Urgency |

### Audio Generation Tools

| Tool | Use Case | Notes |
|------|----------|-------|
| ElevenLabs | Voice synthesis | High-quality TTS |
| Bark | Local voice | Free, variable quality |
| Suno AI | Music generation | Ambient soundscapes |
| AudioCraft | Sound effects | Meta's open-source |

---

## Priority 4: Video/Motion

### Gameplay Integration Points

| Gameplay Moment | AI Content | Trigger | Impact |
|-----------------|------------|---------|--------|
| **Message Travel** | Light-speed visualization | Message sent | Scale of distances |
| **Response Arrival** | Dramatic sequence | Response received | Payoff moment |
| **Attack Countdown** | Fleet approach animation | Warning triggered | Tension |
| **Genesis Project** | Life evolution time-lapse | World seeded | Long-term payoff |
| **Technology Unlocks** | Visual effects | Tech researched | Progress feeling |

### Video Generation Tools

| Tool | Use Case | Notes |
|------|----------|-------|
| Runway Gen-2 | Short clips | AI video generation |
| Stable Video Diffusion | Local generation | Open-source |
| Pika Labs | Animation | Quick iterations |

---

## Technical Integration Architecture

### Current AI Manager

```python
# src/ai_manager.py
class AIManager:
    generate_text(prompt, system_prompt)  # Text generation
    wippy_civ_response(params)            # Via Wippy runtime
    wippy_director_log(params)            # Narrative generation
    wippy_learn(outcome)                  # Adaptive learning
```

### Proposed Extensions

```python
# src/ai_content_manager.py
class AIContentManager(AIManager):
    """Extended AI manager with multimedia generation capabilities."""

    # Image Generation
    def generate_star_portrait(self, system_data: dict) -> str:
        """Generate unique visualization for a star system."""
        pass

    def generate_artifact_visualization(self, swan_song_type: str) -> str:
        """Generate visual representation of extinct civ artifacts."""
        pass

    def generate_event_imagery(self, event_type: str, context: dict) -> str:
        """Generate abstract imagery for philosophical events."""
        pass

    def generate_director_portrait(self, director: dict) -> str:
        """Generate portrait for current program director."""
        pass

    # Audio Generation
    def generate_signal_audio(self, pattern: str, civ_type: str) -> str:
        """Synthesize alien transmission sounds."""
        pass

    def generate_ambient_soundscape(self, era: int, tech_level: int) -> str:
        """Generate era-appropriate background audio."""
        pass

    def synthesize_voice(self, text: str, speaker_type: str) -> str:
        """Convert text to speech with appropriate voice."""
        pass

    # Video Generation (future)
    def generate_contact_animation(self, message_data: dict) -> str:
        """Generate message travel visualization."""
        pass

    def generate_countdown_visualization(self, eta_generations: int) -> str:
        """Generate attack countdown animation."""
        pass
```

### Wippy Integration

Add new processes to `wippy_ai/src/processes/`:

- `image_gen.lua` - Image generation orchestration
- `audio_gen.lua` - Audio synthesis coordination
- `content_cache.lua` - Cache generated content for reuse

### Configuration

```json
// data/ai_content_config.json
{
  "image_generation": {
    "enabled": true,
    "provider": "stable_diffusion",
    "cache_dir": "./media/generated/images",
    "style_preset": "sci-fi_minimalist"
  },
  "audio_generation": {
    "enabled": true,
    "provider": "local_tts",
    "cache_dir": "./media/generated/audio"
  },
  "video_generation": {
    "enabled": false,
    "provider": "runway",
    "max_duration_seconds": 10
  }
}
```

---

## Implementation Phases

### Phase 4A: Image Integration
- Add image display capability to terminal/UI
- Integrate image generation API (DALL-E, Stable Diffusion, local)
- Implement star system portraits
- Add swan song artifact visuals
- Generate director portraits

### Phase 4B: Enhanced Text
- Dynamic philosophical event descriptions
- Director personality-driven commentary
- Procedural news headlines per generation
- Civilization encyclopedia entries
- Extended victory/defeat narratives

### Phase 4C: Audio Integration
- Signal audio synthesis
- Ambient soundscape system
- Voice narration for key moments
- WOW! signal audio recreation
- Swan song "voice" effects

### Phase 4D: Video/Motion
- Message travel animations
- Attack countdown visuals
- Victory/defeat cinematics
- Genesis Project evolution time-lapse

---

## Cost Considerations

| Content Type | Free Option | Paid Option | Est. Cost/Game Session |
|--------------|-------------|-------------|------------------------|
| Text | Ollama (local) | Claude/GPT-4 | $0.01-0.05 |
| Images | Stable Diffusion | DALL-E 3 | $0.10-0.50 |
| Audio | Bark/TTS | ElevenLabs | $0.05-0.20 |
| Video | SVD (limited) | Runway | $0.50-2.00 |

**Recommendation:** Default to local/free options with paid API fallbacks for enhanced quality.

---

## Related Documentation

- [Design Notes](design_notes.md) - Section 9: AI-Enhanced Gameplay
- [AI Advisor Implementation](ai_advisor_implementation.md)
- [Development Roadmap](development_roadmap.md)
- [Wippy AI Runtime](../wippy_ai/README.md)
