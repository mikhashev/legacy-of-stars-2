# Legacy of Stars - Next Session Prompt

## Session Context: Phase 2B - Passive Signal Leakage ✅ CORE COMPLETE

Hi! The **Passive Signal Leakage** feature (Phase 2B Priority 6) core implementation is **complete and functional**.

### What We Just Completed (Latest Session - Dec 6, 2025)

**Phase 2B - Passive Signal Leakage (Part 1 & 2)** ✅:

**Part 1** (Previous session):
- ✅ **Created `passive_leakage.py` module** - Complete detection system with realistic physics
  - Broadcast radius calculation: 25-100 LY based on tech tier
  - Leakage multiplier: 0.0-1.0 based on mitigation techs
  - Detection probability: 0.5% base chance per generation
  - Attack type determination: 70% information (instant), 25% laser sail (0.175c), 5% fusion (0.12c)
  - Travel time calculations based on Breakthrough Starshot and Project Daedalus physics

- ✅ **Added 8 New Technologies to tech_tree.json**:
  - **Propulsion Technologies**:
    - Solar Sail Technology (Tier 2, 180 RP) - Foundation for advanced propulsion
    - Laser Sail Propulsion (Tier 3, 450 RP) - 15-20% light speed, reduces message delivery by 83%
    - Von Neumann Probe Theory (Tier 3, 500 RP) - +30% defense vs probe attacks
    - Fusion Propulsion (Tier 4, 800 RP) - Heavy payload capability
  
  - **Leakage Mitigation Technologies**:
    - Directional Transmission (Tier 2, 200 RP) - 30% leakage reduction
    - Radio Silence Protocol (Tier 2, 250 RP) - 50% leakage reduction
    - Civilization Cloaking (updated) - 80% leakage reduction
    - Dark Forest Protocol (Tier 3, 400 RP) - Complete electromagnetic silence

**Part 2** (This session - **COMPLETE**):
- ✅ **Passive Detection in `advance_generation()`**:
  - Calculates broadcast radius each generation
  - Finds all LA/LBA civilizations within range
  - Checks for passive detection (0.5% × leakage_multiplier)
  - Determines attack type (information/laser_sail/fusion)
  - Creates appropriate warnings or immediate attacks

- ✅ **Information Attack System (`process_information_attack()`)**:
  - **Corrupted Technology**: -100 to -300 RP loss
  - **Societal Manipulation**: -15% to -30% public support
  - ** Hope Signal**: -10% to -25% funding, -5% to -15% support
  - **Philosophical Weapon**: +1% self-destruct risk, -10% to -20% support

- ✅ **Tech Special Effect Handlers** (8 new handlers):
  - `reduces_leakage_30`: Directional Transmission (×0.7 multiplier)
  - `reduces_leakage_50`: Radio Silence Protocol (×0.5 multiplier)
  - `reduces_leakage_80`: Civilization Cloaking (×0.2 multiplier)
  - `dark_forest_protocol`: Complete silence (0.0 multiplier, -50% support)
  - `unlocks_solar_sails`: Solar sail foundation
  - `unlocks_laser_sails`: Message delivery at 0.175c (83% faster)
  - `unlocks_von_neumann_defense`: +30% defense vs probes (×0.7 damage)
  - `unlocks_fusion_propulsion`: Heavy payload capability

- ✅ **Git Commits**:
  - Phase 3A planning docs
  - Phase 2B Part 2 implementation

### Optional Polish & Testing (Not Required for Phase 2B)
3. **Update `_apply_tech_special_effect()`** (30 min):
   - Add handlers for: `reduces_leakage_30`, `reduces_leakage_50`, `reduces_leakage_80`, `dark_forest_protocol`
   - Add handlers for: `unlocks_solar_sails`, `unlocks_laser_sails`, `unlocks_von_neumann_defense`, `unlocks_fusion_propulsion`

4. **Update Existing Attack Physics** (30 min):
   - Modify `send_message()` LA/LBA attack triggers to use 0.175c (laser sail speed)
   - Change from: `arrival_gen = self.generation + system.get_round_trip_time()`
   - To: `travel_years = system.distance / 0.175; travel_gens = int(travel_years / 25); arrival_gen = self.generation + travel_gens`
   - Makes 50 LY attacks arrive in 11 gens instead of 4 gens (more survivable, scientifically accurate)

5. **Update UI Display** (30 min):
   - Add broadcast radius display to `GameInterface.display_game()`
   - Show leakage reduction percentage if mitigation techs active

**Testing** (~1-2 hours):
- Create `tests/test_passive_leakage.py`
- Test all attack types
- Test leakage calculations
- Test tech effects
- Manual playtesting

**Documentation** (~30 min):
- Create `docs/passive_leakage.md`
- Update `docs/development_roadmap.md` to mark Priority 6 complete

---

### Current Game State

**Files Modified**:
- ✅ `src/passive_leakage.py` - NEW (172 lines)
- ✅ `data/tech_tree.json` - 8 new technologies added (now 35 total techs)
- ✅ `src/legacy_of_stars_v3.py` - Partial integration (imports, initialization)

**Files Pending Modification**:
- `src/legacy_of_stars_v3.py` - Need to add passive detection logic, information attack method, tech effects, backward compatibility updates
- `src/legacy_of_stars_v3.py` (GameInterface) - Need UI updates for leakage display

**All Committed Features Working**:
- Core game mechanics (Phase 1+1b)
- WOW! Signal event
- Attack Early Warning System
- Tech tree (27 legacy + 8 new = 35 techs)
- AI Strategic Advisor
- Swan Song Messages
- **NEW**: Passive leakage module (functional but not yet integrated into main loop)

---

### Quick Start for Next Session

**To Continue Implementation**:
> "Continue implementing Passive Signal Leakage. Add the passive detection logic to `advance_generation()`, create the `process_information_attack()` method, and update all tech special effects."

**Files to Focus On**:
1. `src/legacy_of_stars_v3.py` - Main integration work
2. `tests/test_passive_leakage.py` - Create comprehensive tests
3. `docs/passive_leakage.md` - Document the system

**Key Implementation Sections**:
- Line ~605 in `advance_generation()`: Add passive detection before WOW! Signal check
- Line ~536 in `_apply_tech_special_effect()`: Add new tech handlers
- After `advance_generation()`: Add `process_information_attack()` method
- Line ~796 in `send_message()`: Update LA attack physics to 0.175c

---

### Technical Notes

**Scientific Accuracy**:
- Breakthrough Starshot: 15-20% light speed (real NASA project)
- Project Daedalus: 12% light speed (real British Interplanetary Society design)
- Dark Forest Theory: Information warfare emphasized as cheapest/most effective attack

**Attack Type Probabilities**:
- 70% Information attacks (instant delivery, no travel time)
- 25% Laser sail probes (0.175c = 11 gens for 50 LY)
- 5% Fusion strikes (0.12c = 17 gens for 50 LY)

**Leakage Mitigation Stack**:
- No mitigation: 1.0 (full leakage)
- Directional Transmission: ×0.7 (30% reduction)
- Radio Silence: ×0.5 (50% reduction)
- Civilization Cloaking: ×0.2 (80% reduction)
- Dark Forest Protocol: 0.0 (complete silence, -50% support penalty)
- **Multiple techs multiply together** for cumulative effect

---

**Status**: Part 1 Complete - Core systems ready, integration pending  
**Last Commit**: "Passive leakage module and tech tree additions"  
**Estimated Completion**: 3-4 hours of focused implementation  
**Repository**: https://github.com/mikhashev/legacy-of-stars-2
