# Legacy of Stars - Development Roadmap
**Updated**: 2025-12-04 based on design discussions

## ✅ Phase 1+1b: COMPLETE (Dark Forest Core)

### What We Built
**Statistical Realism:**
- ✅ 75/25 age distribution (75% civs older than humanity)
- ✅ Extinct civilizations (15% chance)
- ✅ Swan song data archive flags (80% of extinct civs)
- ✅ Age-based tech stage progression
- ✅ Deception capability (scales with civilization age)

**Dark Forest Mechanics:**
- ✅ Hidden strategies (L/LB/LR/LA/LBA) with weighted probabilities
- ✅ Strategy-based message responses
- ✅ Attack system for hostile civilizations (LA/LBA)
- ✅ Deceptive bait mechanics (LBA high-deception trap)
- ✅ Tiered attack consequences based on tech gap

**Developer Experience:**
- ✅ Timestamped session logs (`game_YYYYMMDD_HHMMSS.log`)
- ✅ Debug logging showing all strategies at game start
- ✅ Extinct civilization display fix
- ✅ Comprehensive test suite

### Files Delivered
- `legacy_of_stars_v3.py` - Main game with Dark Forest mechanics
- Test scripts: `test_v3.py`, `test_phase1.py`, `test_debug_log.py`

---

## 🎯 Phase 2A: Historical Foundation & Tutorial (IMMEDIATE - Week 1)

### Priority 1: WOW! Signal Tutorial ⭐⭐⭐⭐ **NEW!**
**Purpose**: Introduce players to Dark Forest themes through historic event
**User Decision**: Tutorial/Intro Scenario approach

**Implementation:**
1. **Game Start Year: 1977** (August 15 - WOW! Signal date)
   - Tutorial opens with Dr. Jerry Ehman discovering signal
   - Player makes first critical decision about response
   - Choice affects starting bonuses and gameplay approach

2. **Tutorial Narrative**
   - Real historical context (Big Ear telescope, "Wow!" moment)
   - Four response options: Reply, Monitor, Cautious, Analyze
   - Each choice provides different starting advantage
   - Transitions to 2025 campaign start

3. **Starting Bonuses by Choice**
   - **Reply**: +20% LA/LBA detection (learned from risk)
   - **Monitor**: +10% all detection (focused approach)
   - **Cautious**: -10% attack damage (defensive mindset)
   - **Analyze**: +50 starting RP (scientific method)

**Timeline**: 1 day implementation
**Impact**: VERY HIGH - perfect thematic intro, teaches mechanics

---

### Priority 2: Attack Early Warning System ⭐⭐⭐ **NEW!**
**Purpose**: Realistic defense - no FTL means time to prepare
**User Feedback**: "Earth can wait for arrival and prepare"

**Implementation:**
1. **Early Detection**
   - When LA/LBA attack triggered, player gets warning
   - Warning appears immediately: "Hostile fleet detected!"
   - Preparation time = light-speed travel time (round trip)
   
2. **Defensive Actions Available**
   - "Emergency Defense Protocol" (all AP, +50% defense)

---

   - "Emergency Defense Protocol" (all AP, +50% defense)
   - "Evacuate Critical Infrastructure" (reduce casualties 30%)
   - "Attempt Diplomatic Contact" (hail mary, might work on low-deception LBA)

3. **Tech-Based Improvements**
   - "Orbital Defense Grid" (passive 40% damage reduction)
   - "Early Warning Network" (+2 generation warning time)
   - "Distributed Civilization" (off-world backups, attack can't destroy Earth)

4. **Countdown UI**
   - Log shows: "⚠️ HOSTILE FLEET ETA: X generations"
   - Tension builds as deadline approaches
   - Player must balance defense vs. other needs

**Timeline**: 1-2 days implementation
**Impact**: VERY HIGH - realistic, strategic, fair, tense

---

### Priority 3: Realistic Tech Tree Redesign ⭐⭐⭐ **NEW!**
**Purpose**: SETI-specific, historically accurate technology progression
**User Feedback**: "Tech tree now is not correct from real view"

**Historical Timeline (Start: 1977):**

**Tier 0 (1977-2000) - Gen 1-2:**
- Arecibo Radio Telescope (real, built 1963)
- Drake Equation Analysis (published 1961)
- Basic Signal Processing (1970s tech)
- Project Ozma Methods (first SETI search, 1960)
- Voyager Golden Record (sent 1977)

**Tier 1 (2000-2050) - Gen 2-3:**
- SETI@Home Distributed Computing (launched 1999)
- Deep Space Network Upgrade (NASA DSN)
- Optical SETI (laser detection)
- Kepler Exoplanet Database (target selection)
- AI Pattern Recognition (ML for signals)

**Tier 2 (2050-2100) - Gen 3-5:**
- Square Kilometre Array (SKA) - world's largest telescope
- Breakthrough Listen (real $100M initiative)
- Quantum Communication Detection
- Technosignature Cataloging (industrial pollution detection)
- **AI Strategic Advisor** ⭐ (NEW!)

**Tier 3 (2100-2200) - Gen 5-8:**
- Neutrino Telescope Networks
- Gravitational Wave Communication
- Dyson Sphere Detection Systems
- Orbital Defense Grid (anti-LA protection)
- Civilization Cloaking (hide Earth's signals)

**Tier 4 (2200-2400+) - Gen 8-15:**
- Relativistic Communication (near-light speed)
- Distributed Backup Colonies (Mars/Europa refuges)
- Stellar Engineering (manipulate stars for signaling)
- Post-Biological Transition Tech
- Emergency Evacuation Infrastructure

**Generation Gating:**
```python
# Tech unlocks based on realism, not just prerequisites
tech.min_generation = calculated_from_year
# Example: Quantum tech unavailable until Gen 4 (2075)
```

**Timeline**: 2-3 days (redesign + implementation)
**Impact**: HIGH - makes game feel realistic and grounded

---

### Priority 4: AI Strategic Advisor ⭐⭐⭐⭐ **NEW!**
**Purpose**: Meta-brilliant - AI helping you play game about alien AI
**User Idea**: "AI assistant that can receive current context and give advice"

**Implementation:**
1. **Tech Unlock**: "AI Strategic Advisor" (Tier 2, ~Gen 4, Cost: 200 RP)
   - Prerequisites: Digital Signal Processing, Linguistic AI
   - Description: "Advanced AI analyzes galactic patterns and provides strategic recommendations"

2. **Context Analysis**
   ```python
   class AIAdvisor:
       def get_advice(self, game_state):
           context = f"""
           Generation {gen}, Year {year}
           Support: {support}%, Funding: {funding}%
           Civilizations: {known_count} detected, {contacted} contacted
           Responses: {responses_received}
           Active Threats: {pending_attacks}
           Recent Events: {last_5_events}
           """
           
           prompt = "You are Earth's strategic AI advisor for SETI.
           Analyze threats, identify safe contacts, recommend actions.
           Remember Dark Forest theory - silence might be safer."
           
           return ai_manager.generate_text(context, prompt)
   ```

3. **New Action**: "Consult AI Advisor" (Free, once per generation)
   - Shows strategic briefing in game log
   - Provides:
     - Risk assessment (current dangers)
     - Pattern analysis (suspicious silent systems)
     - Recommended actions (what to do this turn)
     - Long-term strategy (next 3-5 generations)

4. **Example Output**:
   ```
   === AI STRATEGIC BRIEFING - Gen 8 ===
   
   RISK: MODERATE
   - Support declining (48%), recommend outreach
   - No active threats
   - Ecological risk increasing
   
   OBSERVATIONS:
   - Proxima: No response to 3 messages (L or LA?)
   - Tau Ceti: Enthusiastic responses (verified LB-SAFE)
   - Wolf 359: EXTINCT - potential swan song
   
   RECOMMENDED:
   1. Public Outreach (support critical)
   2. Research Wolf 359 (archives?)
   3. AVOID Proxima (suspicious silence)
   
   FORECAST: Defunding risk by Gen 12 unless support restored
   ```

**Timeline**: 2-3 days implementation
**Impact**: VERY HIGH - helps players, thematically perfect, unique feature

---

## 🎯 Phase 2B: Content & Discovery (Week 2-3)

### Priority 5: Swan Song Messages ⭐⭐⭐
**Purpose**: Make extinct civilizations meaningful

**Implementation:**
- AI-generated final messages from dead civilizations
- Discovery mechanic: "Deep Scan for Artifacts" action
- Categories: Warnings, Archives, Technical Data, Pleas
- Rewards: Tech hints, lore, philosophical insights

**Timeline**: 2 days
**Impact**: HIGH - narrative depth

---

### Priority 6: Passive Signal Leakage ⭐⭐
**Purpose**: Authentic Dark Forest risk - we broadcast accidentally

**Implementation:**
- Tech level determines broadcast radius
- LA/LBA can detect Earth WITHOUT being contacted
- Mitigation tech: Radio Silence, Quantum Encryption
- Creates existential tension

**Timeline**: 2-3 days
**Impact**: VERY HIGH - changes core tension

---

## 📊 Revised Development Order

### **Immediate (Phase 2A - Week 1)**
1. ✅ **Commit Phase 1+1b** (today)
2. 🔨 **WOW! Signal Tutorial** (1 day) - thematic intro
3. 🔨 **Attack Early Warning** (1-2 days) - realistic defense
4. 🔨 **Tech Tree Redesign** (2-3 days) - historical accuracy

### **Short-term (Phase 2B - Week 2)**
5. 🔨 **AI Strategic Advisor** (2-3 days) - meta-feature
6. 🔨 **Swan Song Messages** (2 days) - extinct civ content

### **Medium-term (Phase 2C - Week 3)**
7. 🔨 **Passive Signal Leakage** (2-3 days) - core tension
8. 🔨 **Defensive Technologies** (1-2 days) - player agency
9. 🔨 **Victory Condition Alternatives** (1 day) - replayability

---

## 🎮 Updated Playtest Priorities

**Before Phase 2A:**
- ✅ Verify all 5 strategies
- ✅ Test attack system
- ⚠️ Need: LBA deceptive trap test
- ⚠️ Need: Victory condition test (3 contacts)

**After Phase 2A (WOW Tutorial):**
- Test all 4 tutorial choices
- Verify 1977 start year accuracy
- Confirm starting bonuses work
- Test attack preparation mechanics

---

## 💡 Key Design Decisions Made

1. **Start Year**: 1977 (WOW! Signal era) ✅
2. **Tutorial**: WOW! Signal intro scenario ✅
3. **Attack Defense**: Early warning + preparation window ✅
4. **Tech Tree**: Historically accurate, generation-gated ✅
5. **AI Advisor**: Real AI provides strategic guidance ✅

---

## 📈 Success Metrics

**Phase 2A Goals:**
- [ ] WOW! Signal tutorial is engaging and educational
- [ ] Attack preparation creates strategic depth
- [ ] Tech tree feels realistic (1977-2477 timeline)
- [ ] Players understand game mechanics after tutorial

**Phase 2B Goals:**
- [ ] AI Advisor provides genuinely helpful guidance
- [ ] Swan songs feel authentic and meaningful
- [ ] Passive leakage creates genuine tension
- [ ] 15+ hours of engaging gameplay

---

**Current Status**: Phase 1+1b COMPLETE ✅  
**Next Milestone**: WOW! Signal Tutorial (Phase 2A)  
**Target**: Playable Phase 2A in 1 week, Full Phase 2 in 3 weeks

1. **Leakage System**
   - Tech level determines broadcast radius
   - Higher tech = louder signals = more danger
   - Player can research "Radio Silence Protocol" to reduce leakage

2. **Discovery by Others**
   - Passive chance each generation that LA/LBA detect Earth
   - Attack triggered WITHOUT player sending message
   - Creates authentic existential dread

3. **Mitigation Options**
   - Tech: "Directional Transmission" (reduce leakage 50%)
   - Tech: "Quantum Encryption" (reduce leakage 80%)
   - Doctrine: "Dark Forest Protocol" (stop all outbound, -50% support)

**Complexity**: Medium-High (4-5 hours)  
**Impact**: Very High - changes core tension, makes silence a strategy

---

### Priority 3: Tech Tree Expansion ⭐⭐
**Purpose**: More player agency and strategic options

**New Technologies:**
1. **Defensive Tech**
   - "Asteroid Defense Grid" - Reduces LA attack severity
   - "Early Warning System" - 2 generation advance notice of attacks
   - "Stellar Camouflage" - Reduces passive leakage detection chance

2. **Communication Tech**
   - "Linguistic AI" - +20% message quality
   - "Cultural Database" - Better responses from LB/LR civilizations
   - "Deception Analysis" - Chance to detect LBA traps

3. **Social Tech**
   - "Unified Earth Government" - Larger action point pool
   - "Generational Archives" - Slower knowledge decay

**Complexity**: Low-Medium (2-3 hours)
**Impact**: Medium - adds depth, player choices

---

## 🚀 Phase 3: Polish & Player Experience

### Priority 1: Victory Condition Alternatives ⭐
**Current**: Contact 3 civilizations  
**Problem**: Encourages risky broadcasts

**New Victory Modes:**
1. **Survival Score**
   - Generations survived × (Contacts made + Knowledge gained)
   - Encourages balance between caution and exploration

2. **Knowledge Victory**
   - Reach 100% knowledge base without triggering attacks
   - Pure research/observation path

3. **Diplomatic Victory**
   - Establish verified-peaceful contact with 2+ civilizations
   - Must correctly identify and avoid LA/LBA

**Complexity**: Low (1-2 hours)
**Impact**: High - better replay value

---

### Priority 2: Risk Calculator UI ⭐⭐
**Purpose**: Help players make informed SETI/METI decisions

**Features:**
- Visual display of current broadcast risk
- Shows: Passive leakage radius, contacted systems, estimated danger
- "What-if" simulator: "If I message this system, risk becomes..."
- Warning indicators for suspicious behavior patterns

**Complexity**: Medium (3-4 hours, depends on UI framework)
**Impact**: Medium - improves player understanding

---

### Priority 3: Enhanced Narrative System ⭐
**Purpose**: Make each playthrough feel unique

**Features:**
1. **Procedural Events**
   - Rogue AI warning from friendly LB civilization
   - Intercepted message between two other civilizations
   - Evidence of ancient war (extinct LA civilization found near extinct victim)

2. **Dynamic Descriptions**
   - AI-generated system descriptions based on age/stage
   - Unique alien culture details for LB civilizations
   - Environmental storytelling through research discoveries

**Complexity**: Medium-High (4-6 hours)
**Impact**: High - massively improves immersion

---

## 📊 Recommended Development Order

### Immediate Next Steps (Phase 2A - 1 week)
1. ✅ **Commit Phase 1+1b** (today)
2. 🔨 **Swan Song Messages** (2-3 days)
   - Design message categories
   - Implement discovery mechanic
   - AI prompt engineering for authentic last messages
3. 🔨 **Passive Leakage** (2-3 days)
   - Basic leakage calculation
   - LA/LBA detection of Earth
   - Mitigation tech tree additions

### Medium Term (Phase 2B - 2 weeks)
4. 🔨 **Tech Tree Expansion** (3-4 days)
   - Add 10-15 new technologies
   - Balance costs and prerequisites
   - Doctrine choices for key techs

5. 🔨 **Victory Condition Alternatives** (1-2 days)
   - Implement scoring system
   - Add end-game summary screens

### Longer Term (Phase 3 - 1 month)
6. 🔨 **Risk Calculator UI** (1 week)
7. 🔨 **Enhanced Narrative** (1-2 weeks)
8. 🔨 **Final Polish** (1 week)
   - Balancing pass
   - Bug fixes
   - Playtesting

---

## 🎮 Playtest Priorities

**Before starting Phase 2:**
1. ✅ Verify all 5 strategies work correctly
2. ✅ Confirm attack system triggers properly
3. ✅ Test extinct civilization discovery flow
4. ⚠️ **Need to test**: LBA deceptive trap (high deception)
5. ⚠️ **Need to test**: LA/LBA attacks with different tech gaps
6. ⚠️ **Need to test**: Victory condition (3 contacts)

**Suggested Playtest:**
- Message 5+ different systems
- Document which strategies appear in logs
- Try to trigger both LA and LBA attacks
- Test extinction discovery at different knowledge levels

---

## 🔧 Technical Debt & Improvements

### Code Quality
- [ ] Move strategy constants to config file
- [ ] Refactor `send_message()` into smaller methods
- [ ] Add type hints throughout
- [ ] Create unit tests for strategy selection

### Performance
- [x] Logging system (optimized with timestamps)
- [ ] Save/Load game state
- [ ] Automated playtest suite

### Documentation
- [x] Implementation guide (phase1b_implementation_guide.md)
- [x] Walkthrough (walkthrough.md)
- [ ] Player manual
- [ ] Strategy guide (spoiler version showing all mechanics)

---

## ❓ Open Design Questions

1. **Swan Song Rewards**: Should they unlock full tech or just hints?
2. **Passive Leakage Rate**: What's the sweet spot for danger vs. playability?
3. **LBA Deception Success**: Current 70% for high-deception - too easy to fall for?
4. **Attack Defense**: Should there be a chance to survive LA attacks?
5. **Silent Civilizations (L)**: Should they ever break silence under special circumstances?

---

## 📈 Success Metrics

**Phase 2 Goals:**
- [ ] Swan song messages feel authentic and meaningful
- [ ] Passive leakage creates genuine tension
- [ ] Players have meaningful defensive options
- [ ] Tech tree offers real strategic choices
- [ ] 10+ hours of engaging gameplay

**Phase 3 Goals:**
- [ ] Multiple victory paths feel balanced
- [ ] Risk calculator helps players understand decisions
- [ ] Each playthrough feels narratively unique
- [ ] Game has lasting appeal beyond initial discovery

---

## 🌟 Stretch Goals (Phase 4+)

- **Multiplayer**: Civilizations are other players
- **Custom Scenarios**: Preset galaxy configurations
- **Modding Support**: JSON-based civilization definitions
- **Timeline Visualization**: Graph of all events over generations
- **Steam Release**: Polish for public distribution

---

**Current Status**: Phase 1+1b COMPLETE ✅  
**Next Milestone**: Swan Song Messages (Phase 2A)  
**Target**: Playable Phase 2 in 2 weeks
