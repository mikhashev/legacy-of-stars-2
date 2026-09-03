# Swan Song Messages - Feature Documentation

**Status**: ✅ **COMPLETE** - Phase 2B Priority 5  
**Implemented**: 2025-12-05  
**Impact**: HIGH - Adds narrative depth and strategic rewards to extinct civilizations

---

## Overview

Swan Song Messages bring extinct civilizations to life by allowing players to discover their final transmissions. These poignant messages provide strategic rewards, cautionary tales, and emotional depth to the Dark Forest universe.

## Core Mechanics

### Discovery System

**Requirements:**
- Target system must contain an extinct civilization with a swan song (80% chance)
- Minimum 30% knowledge of the system required
- Costs 1 Action Point to attempt discovery

**Discovery Probability:**
- 30% knowledge: 50% success chance
- 60% knowledge: 100% success chance
- Linear scaling between these thresholds

**Access:**
- New menu option: "🕊️ Listen for Swan Song" (shown when undiscovered swan songs exist)
- Lists all extinct systems with knowledge levels
- Shows which systems have sufficient knowledge for discovery

### Message Categories

Swan Songs are categorized into 5 types with different rewards:

#### 1. **WARNING** (30% chance)
- **Theme**: Dark Forest warnings from victims of hostile contact
- **Rewards**: 
  - +20 Knowledge
  - +100 Research Points
  - -5% Public Support (frightening revelation)
- **Example**: "THEY ARE LISTENING. SILENCE IS SURVIVAL."

#### 2. **ARCHIVE** (25% chance)
- **Theme**: Preserved knowledge from civilizations that saw their end coming
- **Rewards**:
  - +30 Knowledge
  - +150 Research Points
  - Tech Hint (helps identify next useful technology)
- **Example**: "Our knowledge dies with us. Preserve yours better than we did."

#### 3. **TECHNICAL** (20% chance)
- **Theme**: Technical schematics and research data
- **Rewards**:
  - +250 Research Points
  - **25% discount on next technology research!**
- **Example**: "Technology without wisdom leads only to ash."

#### 4. **PLEA** (15% chance)
- **Theme**: Desperate calls for help that never came
- **Rewards**:
  - +15 Knowledge
  - +50 Research Points
  - -10% Public Support (deeply disturbing)
- **Example**: "We are alone. We die alone. Don't make our mistake."

#### 5. **PHILOSOPHY** (10% chance)
- **Theme**: Reflections on existence and civilization's legacy
- **Rewards**:
  - +10 Knowledge
  - +75 Research Points
  - +10% Public Support (inspirational)
- **Example**: "Stars don't care. The universe doesn't remember. Only each other matters."

### Bonus Rewards

**Ancient Civilization Bonus:**
- Civilizations older than 100,000 years grant +100 additional Research Points
- Indicated in reward message: "(Ancient civilization bonus!)"

---

## Gameplay Flow

### 1. Research Phase
Players must first research extinct systems to build knowledge:
```
Action: Focus Research on Star System
→ Build knowledge to 30%+ for swan song detection
```

### 2. Discovery Phase
Once 30%+ knowledge is reached:
```
Menu Option: 🕊️ Listen for Swan Song (X undiscovered)
→ Select extinct system
→ Probability-based discovery attempt
```

### 3. Revelation Phase
On successful discovery:
```
Display:
- Full swan song message (AI-generated or fallback)
- Category and extinction details
- Applied rewards
```

### 4. Strategic Application
**Tech Discount Usage:**
- Automatically applied to next tech researched
- Can save 25% on expensive Tier 3+ technologies
- One-time use, consumed after application

---

## Technical Implementation

### Key Files

**`swan_song_messages.py`** - Core system
- `SwanSong` class: Individual message data
- `SwanSongManager` class: Discovery mechanics
- AI integration for message generation
- Fallback messages for AI failures

**`legacy_of_stars_v3.py`** - Game integration
- `listen_for_swan_song()` method: Player action
- Swan Song Manager initialization
- Reward application logic
- Tech discount integration in `research_tech()`

**`test_swan_songs.py`** - Test suite
- Creation mechanics
- Discovery probability
- Reward categories
- Tech discount system
- Message generation

### AI Integration

**Message Generation:**
```python
prompt = """You are writing the final transmission of an extinct alien 
civilization. Context: [age, extinction time, category, circumstances]

Write a poignant, authentic final transmission (150-300 words) that:
1. Reflects their category
2. Feels like a real final message
3. Provides useful insight/warning for Earth
4. Has emotional weight
5. Written from THEIR perspective
"""
```

**Fallback System:**
- If AI returns empty or fails, uses pre-written fallback messages
- Ensures every swan song has meaningful content
- Maintains immersion even with AI issues

---

## Strategic Considerations

### For Players

**Early Game (Gen 1-5):**
- Research extinct systems to 30% knowledge
- Prioritize WARNING category for Dark Forest intelligence
- Save TECHNICAL discoveries for expensive Tier 2+ techs

**Mid Game (Gen 6-15):**
- ARCHIVE swan songs provide excellent knowledge boost
- Use tech discounts on Tier 3 technologies (200+ RP cost)
- Balance public support losses from PLEA/WARNING

**Late Game (Gen 16+):**
- PHILOSOPHY messages help maintain public support
- Ancient civilization bonuses add up (100+ RP each)
- Complete collection for comprehensive galactic history

### Risk/Reward Balance

**Benefits:**
- Significant research acceleration (50-250 RP per discovery)
- Knowledge accumulation toward victory condition
- Strategic tech discounts (25% = 50-75 RP saved on advanced tech)

**Costs:**
- 1 AP per discovery attempt (probabilistic)
- Some categories decrease public support (-5% to -10%)
- Requires investment in researching extinct systems first

---

## Design Philosophy

### Narrative Goals

1. **Make Extinction Meaningful**: Dead civilizations tell stories
2. **Dark Forest Context**: Many were victims, providing warnings
3. **Emotional Impact**: Players feel weight of galactic history
4. **Strategic Depth**: Rewards encourage exploration of all systems

### Balance Considerations

**Discovery Probability:**
- 30% minimum knowledge prevents immediate access
- Probabilistic element adds replayability
- 100% certainty at 60% knowledge rewards thorough research

**Reward Scaling:**
- TECHNICAL (rare, powerful): Big RP boost + discount
- ARCHIVE (common, balanced): Good RP + knowledge
- WARNING (common, narrative): Knowledge + Dark Forest intel
- PLEA (uncommon, risky): Lower rewards but impactful story
- PHILOSOPHY (rare, supportive): Public support maintenance

**AP Economy:**
- 1 AP cost aligns with other research actions
- Failed attempts due to RNG don't waste too much
- Encourages building knowledge before attempting

---

## Future Enhancements

### Potential Additions (Post-Phase 2B)

**Tech Hints System:**
- ARCHIVE swan songs could reveal tech tree paths
- "They had mastered [technology name] before the end..."
- Unlocks preview of locked technologies

**Swan Song Interconnections:**
- Multiple extinct civs in same region reference each other
- Discover evidence of ancient wars
- Piece together galactic history puzzle

**Rare Super-Ancient Messages:**
- Civilizations millions of years old
- Transcendent wisdom or warnings
- Ultra-rare achievements (0.1% chance)

**Interactive Elements:**
- Choose how to interpret technical data
- Public vs. private disclosure decisions
- Different rewards based on player choice

---

## Statistics & Testing

**Test Results (2025-12-05):**
- ✅ All 5 categories generate correctly
- ✅ Discovery probability scales with knowledge
- ✅ Tech discount applies and consumes properly
- ✅ Fallback messages work when AI unavailable
- ✅ Rewards apply correctly to game state

**Expected Player Experience:**
- Average game: 1-2 extinct civilizations with swan songs
- Typical discoveries per playthrough: 0-2 (player dependent)
- Players who prioritize: 3-5+ discoveries possible
- Speedrunners: Often skip entirely (valid strategy)

---

## Achievement Ideas

**For Future Implementation:**

- **"Archaeologist"**: Discover 5 swan songs in one playthrough
- **"Dark Forest Historian"**: Discover all 5 category types
- **"Ancient Voices"**: Discover a swan song from 500,000+ year old civ
- **"Remember Us"**: Complete the game with all swan songs discovered
- **"Tech Archaeologist"**: Save 500+ RP total with swan song discounts

---

## Developer Notes

**Implementation Time:** ~4 hours (design, code, testing, documentation)

**Key Learnings:**
- AI integration needs robust fallbacks for reliability
- Probabilistic mechanics add tension and replayability
- Small public support penalties create meaningful choices
- Tech discounts are highly valued by players

**Code Quality:**
- Fully modular (swan_song_messages.py is standalone)
- Comprehensive test coverage
- Clean integration with main game
- Follows existing code patterns

**Known Limitations:**
- AI messages may vary in quality (fallbacks ensure minimum quality)
- Discovery RNG can frustrate completionists (intentional design)
- No way to preview swan song content before discovery (mystery element)

---

**Related Documentation:**
- `../plans/development_roadmap.md` - Overall project plan
- `phase2a_implementation_notes.md` - Previous phase details
- `tech_tree.json` - Technology definitions

**Last Updated:** 2025-12-05  
**Version:** 1.0 (Phase 2B Implementation)
