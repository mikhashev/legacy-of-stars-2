# Legacy of Stars — Documentation

Legacy of Stars is a turn-based strategy game about humanity's multi-generational effort to make
contact with alien civilizations: each turn is one generation (~25 years), messages and fleets
travel at light speed or slower, and the answers may be friendship, silence or a fleet. The engine
lives in [`src/`](../src) (no I/O, testable in isolation), the browser build in [`web/`](../web)
(Pyodide + Three.js + Preact on top of the same engine), and the test suites in
[`tests/`](../tests) (Python `unittest`) and `web/tests/` (Vitest + Playwright).

This directory holds four kinds of document: **design** (why the game is the way it is, revised
in place as understanding improves), **plans** (proposals and roadmaps, each carrying its own
status), **reference** (the machine-checkable contract between the engine and the web front-end)
and **history** (implementation notes from earlier phases, kept for the record and never rewritten
except for their header note).

## Design

Living documents: revised in place as the design evolves.

| File | Description | Status |
|------|-------------|--------|
| [design/design_notes.md](design/design_notes.md) | Core design principles — knowledge preservation, dual-use technology, the Great Filter, deep-time survival, and the scientific-realism standard (§8) every other document is checked against. | Living |
| [design/cosmic_game_theory_analysis.md](design/cosmic_game_theory_analysis.md) | Game-theoretic analysis of interstellar-contact strategies, mapped to design opportunities, events and future mechanics. | Living |
| [design/science_accuracy_audit.md](design/science_accuracy_audit.md) | Audit of the implemented rules against `design_notes.md` §8; the basis for `plans/science_accuracy_plan.md`. | Living |

## Plans

Proposals and roadmaps. Each carries a status; a plan is closed by marking it Done, not by moving
or deleting it.

| File | Description | Status |
|------|-------------|--------|
| [plans/development_roadmap.md](plans/development_roadmap.md) | Overall project roadmap: phase history, current release status, what's next. | Living |
| [plans/science_accuracy_plan.md](plans/science_accuracy_plan.md) | Seven-phase plan to bring the game up to its own scientific-realism standard, from `design/science_accuracy_audit.md`. | Done 2026-09-03 |
| [plans/web_version_plan.md](plans/web_version_plan.md) | Plan for the browser build: Pyodide-hosted engine, `web_contract.md`, Three.js scene, Preact UI. | Done 2026-09-03 |
| [plans/civilization_timelines_plan.md](plans/civilization_timelines_plan.md) | Proposal to make alien civilizations change while a message is in flight — light-time as a strategic mechanic, not just a transport delay. | Draft awaiting owner decisions |
| [plans/ai_content_roadmap.md](plans/ai_content_roadmap.md) | Optional LLM-generated text layered over the offline-first content bank; principles and provider setup. | Living |

## Reference

| File | Description | Status |
|------|-------------|--------|
| [reference/web_contract.md](reference/web_contract.md) | The JSON protocol between `src/web_api.py` and the browser front-end (`view_state`, events, `perform`); the specification the TypeScript types are hand-written from. | Living — kept in sync with the code and `tests/test_web_api.py` |

## History

Pre-v1.1 implementation notes, kept for the record; formulas in them may describe superseded
models (see each file's header note where present).

| File | Description | Status |
|------|-------------|--------|
| [history/phase_2a_complete.md](history/phase_2a_complete.md) | Phase 2A implementation notes: attack warning, tech tree redesign, AI advisor. | Historical |
| [history/phase_3a_implementation_plan.md](history/phase_3a_implementation_plan.md) | Phase 3A implementation plan: philosophical-depth events. | Historical |
| [history/tech_tree_redesign.md](history/tech_tree_redesign.md) | Original tech-tree redesign notes (27 technologies / 5 tiers), since superseded by the 44/6 tree. | Historical |
| [history/attack_warning_implementation.md](history/attack_warning_implementation.md) | Attack early-warning system notes, from the pre-0.1c fleet-speed model. | Historical |
| [history/passive_leakage_implementation.md](history/passive_leakage_implementation.md) | Passive signal leakage system notes, from the pre-0.1c fleet-speed model. | Historical |
| [history/swan_song_implementation_summary.md](history/swan_song_implementation_summary.md) | Implementation summary for the swan-song (extinct-civilization final message) feature. | Historical |
| [history/swan_song_messages.md](history/swan_song_messages.md) | Full feature documentation for swan-song messages. | Historical |
| [history/ai_advisor_implementation.md](history/ai_advisor_implementation.md) | AI strategic advisor implementation notes. | Historical |
| [history/personal_context_guide.md](history/personal_context_guide.md) | Guide to using a personal-context JSON template with an AI assistant during development; the origin of this project. | Historical |
| [history/game_development_context_template.json](history/game_development_context_template.json) | The personal-context JSON template referenced by `personal_context_guide.md`. | Historical |

## Conventions

- Docs are English.
- Plans have an owner-decisions section.
- History is never edited except for the header note.
