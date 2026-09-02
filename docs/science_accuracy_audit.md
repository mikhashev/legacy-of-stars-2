# Legacy of Stars — Scientific Accuracy Audit

**Date:** 2026-09-02
**Reviewed:** `src/*.py`, `data/star_catalog.json`, `data/tech_tree.json`, `data/templates/*.json`, `README.md`, `docs/*.md`
**File status:** open, in the repository

The project's own standard is set in `docs/design_notes.md` §8 "Scientific Realism Standards":
no FTL, communication limited to *c*, real spectral classes and habitable zones, evolution by
natural selection. Below is where the game and the documents meet this standard, and where they don't.

---

## 1. Summary

| Area | Assessment | Comment |
|---|---|---|
| Star catalog (distances, spectra, RA/Dec) | ✅ accurate | All 53 entries match reference data within rounding |
| SETI history in the tech tree (dates, projects) | ✅ accurate | Ozma 1960, Drake 1961, Arecibo 1963, Voyager 1977, SETI@home 1999, Kepler 2009, Breakthrough Listen 2015, SKA 2020s |
| Facts about the Wow! signal | ✅ mostly accurate | 1420 MHz, 72 s, 6EQUJ5, Sagittarius, Big Ear; one inaccuracy (see 3.7) |
| Speed of light for messages | ✅ accurate | 2·d / 25 years, rounded up |
| Fleet speeds 0.1c / 0.175c / 0.12c | ✅ plausible | Daedalus 0.12c and Starshot 0.15–0.2c are real project figures |
| Wow! storyline (Gen 144) | ❌ contradicts the game's own physics | Fleet travels at the speed of light; the source is picked from stars ≤ 51 ly instead of ~1800 |
| Years in the tech tree | ❌ arithmetic error | All `year_context` values are offset by +23 years relative to the game's formula |
| The "Genesis" project | ❌ gross violation of biology | Microbes → intelligence in 625 years instead of ~3–4 billion years |
| Habitability / spectral classes | ⚠️ not modeled | Civilizations arise with equal probability at a white dwarf, a giant, and a G star |
| Passive radio leakage | ⚠️ model is inverted | Radius grows with tech level rather than time; Earth is actually getting quieter |
| Extinct civilizations and "swan songs" | ⚠️ causality violation | Went extinct 500–5000 years ago at a distance of 4–50 ly, but we catch the signal now |
| "Faster-than-light" in the INTERSTELLAR stage description | ❌ direct violation of the "no FTL" rule | One line of text |

Overall conclusion: the engine's communication and travel physics are careful, the astronomical
catalog is good, and the SETI chronology is correct. There are three main problems: (1) the Wow!
storyline was written for the old "fleet at light speed" model and is not consistent with 0.1c;
(2) `year_context` in the tech tree counts the year from 2000, while the game counts from 1977;
(3) Genesis violates evolutionary timescales by six orders of magnitude. Everything else consists
of moderate simplifications typical of a strategy game.

---

## 2. What is confirmed as accurate

### 2.1 Star catalog (`data/star_catalog.json`)

All 53 entries were checked. Distances, spectral classes, and J2000 coordinates match
reference values (RECONS, Gaia DR3, SIMBAD) within 0.1 ly and 0.05°.
Examples: Proxima 4.24 ly M5.5V, Tau Ceti 11.91 G8.5V, TRAPPIST-1 40.7 M8V, Van Maanen DZ8.

Notes on the catalog (not errors, but incompleteness and its consequences):

- The comment "Real stars within ~51 light-years" reads as "all stars within this radius."
  In fact it is a selection: within 20 ly it omits, for example, 40 Eridani (16.3), 70 Ophiuchi (16.6),
  36 Ophiuchi, AD Leonis, Groombridge 1618, Gliese 412, as well as the nearest brown dwarfs
  Luhman 16 (6.5) and WISE 0855 (7.4). That's fine for the game, but the comment should be
  reworded to "a selection of real stars."
- Proxima Centauri and Alpha Centauri are one gravitationally bound triple system; in the game
  they are two independent systems, each with its own civilization roll.
- For 82 G. Eridani, G8V is more commonly cited; for Gliese 832, M1.5V; for Epsilon Indi,
  K4V/K5V. The discrepancies are half a subclass, immaterial.

### 2.2 SETI chronology in the tech tree

All real dates are correct: Project Ozma (1960), the Drake equation (1961), Arecibo (1963, 305 m),
the Voyager Golden Record (1977), SETI@home (May 1999), Kepler (March 2009), Breakthrough Listen
(July 2015, $100 million), SKA (construction from December 2022), Breakthrough Starshot (15–20% c,
gram-scale probes), Project Daedalus (BIS, 1973–78, D/He-3, 12% c), IKAROS (2010),
LightSail-2 (2019).

### 2.3 Communication and travel physics in the engine

- `StarSystem.get_round_trip_time` (`src/legacy_of_stars_v3.py:230`): 2·d years / 25, rounded
  up. The README's "12 ly — a reply within a generation" is consistent with this.
- `attack_arrival_generation` (`:711`): d (signal there at the speed of light) + d/0.1 (fleet back)
  = 11·d years. Physically correct for a "retaliatory" fleet.
- The LBA trap: a friendly reply arrives after 2d years, the fleet later — consistent.
- Time dilation at 0.1c (γ = 1.005) and 0.175c (γ = 1.016) is negligible; correctly not modeled.
- The standard 25-year generation is a conventional demographic figure.

### 2.4 The Wow! signal

Date August 15, 1977, 23:16 EDT, Big Ear (Ohio State University), 1420 MHz (hydrogen line),
72 seconds, the recording 6EQUJ5 (peak "U" ≈ 30σ above background), direction — the constellation
Sagittarius near Chi Sagittarii, the signal was never repeated — all correct. The ~1800 ly
estimate flagged as "disputed" is honest: this is the distance to the candidate star
2MASS 19281982-2640123 (Caballero, 2020–22), not a measured distance to the source.

Earth's population of "4 billion" in 1977 is correct (≈4.2 billion). The contents of the 1974
Arecibo message (numbers, atomic numbers, DNA, a human figure, population, the Solar System)
are correct.

### 2.5 Theoretical framework

The L/LB/LR/LA/LBA strategies, the "SETI paradox" (Zaitsev, 2006), the 75/25 rule via
survivorship bias, Dunbar's number (~150) in the "Biology-Technology Gap" event, panspermia,
the Great Filter hypothesis — all correctly presented as hypotheses. "Dark Forest" is presented
as Liu Cixin's theory (2008); it would be worth mentioning the non-fiction predecessor —
David Brin, "The Great Silence" (1983).

---

## 3. Discrepancies

Sorted by severity. "Internal" means a contradiction with the game's own rules,
"scientific" means a discrepancy with established science.

### 3.1 ❌ The Wow! storyline contradicts the 0.1c model (internal + scientific)

Where: `src/wow_signal_event.py:214-215, 232`, `src/game_interface.py:121, 147-148`,
`docs/development_roadmap.md:75, 92`, `docs/phase_2a_complete.md:26, 234`.

1. **A fleet at the speed of light.** The hostile-outcome text reads: "72 generations for our
   message to reach them. 72 generations for their weapons to reach us." That's 1800 ly in 1800
   years — exactly *c*. At the game's adopted speed of 0.1c, a fleet would take 18,000 years
   (720 generations), arriving around generation ~792. The code (`:232`) schedules the attack for
   the current generation, 144.
2. **The source is picked from neighbors.** `_assign_wow_civilization` (`:67`) picks a random
   living civilization from the known systems, all of which are ≤ 51 ly away. A reply from Tau
   Ceti would arrive in 24 years, not 3600. Per the story, the source is in Sagittarius at
   ~1800 ly.
3. **The year 3577.** The UI (`game_interface.py:121`) and two documents state "Gen 144
   (Year 3577)." 144 generations × 25 years = 3600 years → ~5577. Further down on the same
   screen (`:148`), 5577 is already printed. The engine's formula for Gen 144 gives 5552,
   because the event fires at the start of the generation; exactly 3600 years is the start of
   Gen 145 (a minor off-by-one).

Recommendation: add a dedicated "Wow! source (Chi Sagittarii region), ~1800 LY" entry to the
catalog, flagged so it doesn't fall under the regular draw; in the hostile outcome at Gen 144,
what arrives is not a fleet but a *response signal* (an information attack or an announcement),
and if a fleet is needed at all, schedule it at 0.1c with an honest ETA. Replace 3577 with 5577
everywhere.

### 3.2 ❌ `year_context` in the tech tree is offset by +23 years (internal)

Where: `data/tech_tree.json`, all entries with `min_generation ≥ 3`; `src/legacy_of_stars_v3.py:844`.

The year of generation N in the game = 1977 + (N−1)·25. The `year_context` strings were
computed as 2000 + (N−1)·25:

| Technology | min_gen | Year per engine | In `year_context` |
|---|---|---|---|
| Quantum Communication Detection | 4 | 2052 | 2075 |
| Orbital Defense Grid | 5 | 2077 | 2100 |
| Bio-Engineering Foundation | 7 | 2127 | 2150 |
| Consciousness Upload | 15 | 2327 | 2350 |
| Hybrid Civilization | 20 | 2452 | 2475 |
| Solar Sail / Directional Transmission | 3 | 2027 | 2050 |
| AI Pattern Recognition / Planetary Remediation | 3 | 2027 | 2025 |

The player sees one year in the description, and a different one in the "Unlocks in Generation
N (Year …)" message. Recommendation: generate `year_context` from `min_generation` in code, and
remove the string from the JSON.

### 3.3 ❌ The "Genesis" project: evolutionary timescales (scientific)

Where: `src/genesis_project.py:17-19`, `data/tech_tree.json` (genesis_bioprogramming).

Seeded microbes yield complex life after 10 generations (250 years), intelligence after 25
(625 years), spaceflight after 40 (1000 years). On Earth, the path from prokaryotes to
multicellular life took ~2.5–3 billion years, and from the Cambrian to a technological
civilization ~500 million years. "Designed to evolve toward intelligence" cannot compress
natural selection by six orders of magnitude: selection is limited by organisms' generation
times and mutation counts, not by a designer's intent.

Related problems:
- Delivery via "laser-sail probes": Starshot probes are flyby-only, with no braking; a
  biocontainer cannot be softly delivered at 0.175c. Flight time (20 ly ≈ 114 years ≈ 5
  generations) is not accounted for — seeding is instantaneous.
- Any system without a civilization can be seeded, including white dwarfs and giants.

Recommendation without losing the mechanic: rename it "embryo/ark seeding" — delivering not
microbes but ready-made engineered organisms/embryos with AI custodians (embryo space
colonization, Crowl et al. 2012). Then "a culture going from scratch to spaceflight in ~1000
years" becomes defensible, and the lines about "genome sung back" can stay. Add flight time to
seed_gen.

### 3.4 ❌ "Faster-than-light communication" in the stage description (internal)

Where: `src/legacy_of_stars_v3.py:272`.

The INTERSTELLAR description at knowledge ≥ 80: "Advanced interstellar civilization with
faster-than-light communication." This directly contradicts `design_notes.md` §8 and the comment
on `FLEET_SPEED_C` (`:701`, "no FTL in this universe"). Replace with "with interstellar probes /
multi-system presence."

### 3.5 ⚠️ Habitability does not depend on star type (scientific, violates design_notes §8)

Where: `src/legacy_of_stars_v3.py:96` (`has_civilization = random() < 0.15` for all).

The catalog contains spectral classes, but they are never used. As a result, a civilization
arises with the same 15% probability at:

- the white dwarf Van Maanen (DZ8; the star went through a red-giant phase, planets in the
  former habitable zone were destroyed);
- the giants Pollux (K0III), Arcturus (K1.5III), Capella (G8III) — off the main sequence,
  habitable zones have shifted;
- the A stars Sirius, Vega, Altair, Fomalhaut, Castor — ages 0.2–0.5 billion years, lifetime
  ~1 billion, by the Earth analogy too little time for complex life.

That's 9 of 53 systems. Recommendation: a weighting factor by spectral class
(G/K ×1.0, M ×0.6, F ×0.5, A ×0.1, III/D ×0). The §8 description "realistic habitable zones"
would then become true at least at the level of the star.

### 3.6 ⚠️ Passive-leakage model (scientific)

Where: `src/passive_leakage.py:32, 56-73, 191`, `src/legacy_of_stars_v3.py:1369-1397`.

1. **The radius grows with tech level, but should grow with time.** The wavefront of the first
   powerful transmissions (1930s) expands by 1 ly per year regardless of tech tier: in 1977 it
   was ~45 ly, in 2027 ~95, by Gen 6 (2102) ~170. The game holds it at 25 ly up to Tier 2 with a
   cap of 100.
2. **The trend runs the wrong way.** Since the 1990s Earth has been getting radio-quieter:
   digital TV, cable, directional satellite beams, lower transmit power. The sources most
   noticeable to a distant observer are military early-warning radars and planetary radars
   (Arecibo/Goldstone), not "distributed computing, SETI arrays" (Tier 2 → 50 LY).
3. **Detectability does not depend on distance.** The inverse-square law is ignored:
   `calculate_detection_probability` takes `distance` and doesn't use it (this is acknowledged in
   the docstring). Realistic detectability of broadband TV leakage is a handful of ly even for an
   Arecibo-class receiver; narrowband radars, tens to hundreds.
4. **The information attack is instantaneous** (`:1092`, "instant, delivered by signal"). A
   signal from a system 50 ly away takes 50 years = 2 generations; after detection, there's also
   a return trip needed. Currently the attack is applied in the same generation as the detection
   roll.
5. Rounding via `int(travel_years / 25)` (`:191`) underestimates laser-probe ETA
   (10 ly → 57 years → 2 generations instead of 3).
6. "Dark Forest Protocol: complete electromagnetic silence" is physically unattainable
   (thermal radiation, city lights, atmospheric technosignatures such as CFCs/NO₂). Acceptable
   as a game abstraction, but the description is better phrased as "near-total."

Recommendation: radius = 1 ly × (year − 1935), tech lowers the detectability *multiplier*;
schedule the information attack ⌈d/25⌉ generations out; use `distance` with probability falling
off as ~1/d².

### 3.7 ⚠️ Extinct civilizations: causality (scientific + narrative)

Where: `src/legacy_of_stars_v3.py:115` (`extinct_years_ago = randint(500, 5000)`),
`data/templates/swan_songs.json`.

A system at distance d ly is seen as it was d years ago. If a civilization at Tau Ceti (12 ly)
died 3000 years ago, its last *living* transmission passed Earth 2988 years ago. Some templates
account for this ("repeated for {extinct_years_ago} years by machines that outlived their
makers" — a beacon), but the "plea" category ("Third day of the fall… last of the power") is a
one-time live transmission that cannot be caught now.

Recommendation: either tie `extinct_years_ago` to distance for the plea/warning categories
(extinct "d ± a few dozen" years ago as measured by our reception time), or explicitly frame the
signal in all categories as an automated, repeating beacon.

### 3.8 ⚠️ "Cataloguing" the sky's brightest stars as new discoveries (narrative)

Where: `src/legacy_of_stars_v3.py:1677, 1682-1694`.

The discovery mechanic takes stars in order of distance, so Sirius (the sky's brightest star),
Procyon, Vega, Altair, and Arcturus appear in the 21st–24th centuries with the text "NEW STAR
SYSTEM CATALOGUED." Of the catalog, only TRAPPIST-1 (1999), Teegarden's Star (2003), GJ 1061
(proximity established in the 1990s), and partly DX Cancri and GJ 1002 are genuinely new after
1977. Recommendation: reword the event as "added to the SETI target list / surveyed" — the
mechanic stays the same, the text becomes honest.

### 3.9 ⚠️ Individual technologies

| Technology | Problem | Type |
|---|---|---|
| Quantum Communication Detection ("detect quantum-encrypted signals") | Quantum communication does not produce a "class of signal" that can be intercepted from outside; entanglement does not carry information (no-communication theorem). | scientific |
| Relativistic Communication ("near-light-speed laser probes, faster message delivery") | A probe at 0.2c is *slower* than a radio signal at *c*. Message delivery cannot be sped up. The `message_delivery_speed = 0.175` flag is unused in the code — good, but the description and `docs/passive_leakage_implementation.md:62` ("reduces round-trip by 83%") are wrong. | scientific + doc |
| Gravitational Wave *Communication* | Generating gravitational waves for communication requires moving stellar masses; as a *detector* of Type II activity it's acceptable speculation. Rename to "Detection." | scientific |
| Bio-Engineering Foundation ("CRISPR techniques", Gen 7 → 2127) | CRISPR-Cas9 editing dates to 2012. A 115-year anachronism. | chronology |
| Atmospheric Scrubbing (Gen 6 → 2102) | Direct air capture of CO₂ has operated industrially since 2017 (Climeworks). | chronology |
| Stellar Engineering (Gen 10 → 2202) | Manipulating a star 225 years after 1977 is extremely optimistic even for speculation; Kardashev II is millennia away by any extrapolation. | chronology |
| Genetic Pacification ("remove aggressive tribal instincts from genome") | Aggression is polygenic and substantially environmental; there is no "tribal instinct gene." Acceptable as speculation, but the phrasing oversimplifies to the point of being wrong. | scientific |
| Neutrino Telescope Networks | IceCube has operated since 2010; neutrino SETI is a real proposal (Learned et al. 2008). Correct. | ✅ |
| Dyson Sphere Detection | G-HAT (2015), Project Hephaistos (2024). Correct. | ✅ |

### 3.10 ⚠️ Minor factual inaccuracies

- `src/game_interface.py:107`: "Dr. Jerry Ehman reviews automated radio telescope data" on the
  night of August 15. Ehman actually saw the printout a few days later (usually cited as August
  18). The wording "reviews" in a same-night scene is inaccurate.
- `docs/development_roadmap.md:151`: "2MASS 19281982-2640123 ruled out" — the star is not
  "ruled out," it remains an unconfirmed candidate. A later hypothesis (Méndez et al., 2024,
  Arecibo Wow! project) proposes a natural origin: a hydrogen cloud brightened by a magnetar
  flare.
- `docs/passive_leakage_implementation.md:353`: "Breakthrough Starshot (NASA/ESA)" — the
  project belongs to Breakthrough Initiatives (Yuri Milner, 2016), not NASA/ESA. `:355`:
  LightSail-2 is Planetary Society, not NASA.
- The "Mirror Civilization" event: "even nuclear detonations" visible at 18–30 ly — gamma
  flashes from nuclear explosions are not detectable at interstellar distances; industrial
  pollution and radio are.
- `src/swan_song_messages.py:148`: the "civ_age > 100000" bonus is unreachable: the maximum
  age in the generator is exactly 100,000 (`uniform(10, 1000) × 100`). The "Ancient Voices:
  500,000+ years" achievement idea is likewise unreachable with the current generator.
- The LB reply "digital_ascended": "parsed in 0.4 seconds and was debated for forty years" —
  but the reply arrives exactly after the round-trip light time; 40 years of debate would push it
  by almost two generations. A purely narrative nitpick.

---

## 4. Discrepancies between documents and code

The documents in `docs/` are a development history; some of them describe models that no
longer exist. The dangerous spots are where a document states a "scientific" model that
contradicts the current code.

| Document | Claim | Current code |
|---|---|---|
| `attack_warning_implementation.md:165, 211` | "Travel time = round-trip light-speed delay", `arrival = gen + ceil(2d/25)` | Fleet at 0.1c: 11·d years (`:711`). The document describes a fleet at the speed of light. |
| `passive_leakage_implementation.md:62, 266` | Laser sails cut the message round trip by 83% | `message_delivery_speed` is unused; the sail gives +10% to the reply chance. |
| `passive_leakage_implementation.md:284-293` | "NEW: attacks at 0.175c", "50 LY: 4 gens → 11 gens" | Retaliatory fleets are at 0.1c; 0.175c applies only to probes after a leak. |
| `tech_tree_redesign.md` | 27 technologies, 5 tiers; Breakthrough Listen Gen 3+ | 44 technologies, 6 tiers (0–5); Breakthrough Listen Gen 2 in the JSON. |
| `development_roadmap.md:44` | "Extinct civilizations (15% chance)" | 15% is the chance of a civilization at all; of those, 25% are extinct (`:96, :113`). |
| `development_roadmap.md:1199` | "41 technologies across 5 tiers" | 44 / 6. The README says 44 / 6 — correct. |
| `cosmic_game_theory_analysis.md:475-476` | The "Ancient Observer" event grants "Quantum Entanglement Communication — instant, no light-speed delay" | Not implemented. **Do not implement it this way**: it violates the no-communication theorem and design_notes §8. |
| `cosmic_game_theory_analysis.md:457-464` | `age_to_kardashev`: 1000 years → Type I, 10,000 → Type II | Not implemented; Type II (10²⁶ W) in 10,000 years is far beyond any extrapolation. Leave as doc-only. |
| `development_roadmap.md:75, 92`, `phase_2a_complete.md:26, 234` | Gen 144 = Year 3577 | The formula gives 5552; the UI prints both 3577 and 5577. |

---

## 5. What to fix first

Order is by the ratio of "severity / effort."

1. **One line:** remove "faster-than-light communication" (`legacy_of_stars_v3.py:272`).
2. **One line:** "Year 3577" → "Year 5577" in `game_interface.py:121` and two documents.
3. **Tech tree:** generate the year from `min_generation`, remove manual `year_context`
   values. While at it: CRISPR → Gen 2–3; rename Gravitational Wave *Communication* →
   *Detection*; rewrite the descriptions of Quantum Communication Detection and Relativistic
   Communication.
4. **Wow!:** a dedicated source entry at ~1800 ly; the hostile outcome at Gen 144 is a signal,
   not a fleet; remove the text "72 generations for their weapons."
5. **Habitability:** a weighting factor for `has_civilization` by spectral class; forbid
   Genesis seeding at D/III stars.
6. **Genesis:** reframe as embryo/ark seeding, add flight time.
7. **Leakage:** radius based on time, detectability ~1/d², a delay for the information attack.
8. **Extinct civilizations:** tie `extinct_years_ago` to distance, or make all signals beacons.
9. **Discovery text:** "catalogued" → "added to target list."
10. **Documents:** mark `attack_warning_implementation.md` and
    `passive_leakage_implementation.md` as outdated (pre-0.1c model), or update the formulas.

Items 1–3 do not change the balance. Items 4–8 change the gameplay and require running
`LOS_SLOW=1 python -m unittest tests.test_balance -v`.

---

## 6. Sources for verification

- RECONS "The 100 nearest star systems"; Gaia DR3; SIMBAD — the star catalog.
- Ehman, J. "The Big Ear Wow! Signal: What We Know and Don't Know About It After 20 Years" (1997).
- Caballero, A. "An approximation to determine the source of the WOW! Signal" (2020/2022) — candidate 2MASS 19281982-2640123.
- Méndez, A. et al., Arecibo Wow! project (2024) — the natural-origin hypothesis.
- Breakthrough Initiatives, Starshot (2016); Bond, A. & Martin, A. "Project Daedalus" (JBIS, 1978).
- Sullivan, W. T. et al. "Eavesdropping: The Radio Signature of the Earth" (Science, 1978) — detectability of the leakage.
- Brin, D. "The Great Silence" (QJRAS, 1983); Zaitsev, A. "The SETI Paradox" (2006).
- Crowl, A. et al. "Embryo Space Colonization to Overcome the Interstellar Time Distance Bottleneck" (JBIS, 2012).
- Learned, J. et al. "Galactic Neutrino Communication" (2008); Wright, J. et al., G-HAT (2015); Suazo, M. et al., Project Hephaistos (2024).
