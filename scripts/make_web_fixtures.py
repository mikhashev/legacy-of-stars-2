"""
Build showcase save fixtures for the web front-end's W4 animations.

Seed-1 games rarely reach the events the star map is built to animate (a hostile fleet, an
alien reply in flight, a landed Genesis colony) within the handful of generations a Playwright
test can afford to play through. This script uses the Python engine directly - the same
`ContactProgram` the console and `src/web_api.py` use - to construct three saves that start
already in those situations, and writes them to `web/tests/fixtures/` for
`web/tests/showcase.spec.ts` to load through the Load screen's "Import JSON file" button.

Nothing here is a new rule: every fixture only sets fields the engine itself would set (a
system's rolled civilization profile, `true_strategy`, `pending_responses`) or calls existing
methods (`send_message`, `genesis.seed_world`, `advance_generation`). The three fixtures:

    threat.json   a hostile fleet is inbound, ETA >= 3 generations
    reply.json    a system has a reply in flight (`pending_responses` populated)
    genesis.json  a Genesis ark has landed (`evolution_stage` >= 1)
    gameover.json the run has ended (`game_over`), so loading it opens the final report

Usage: python scripts/make_web_fixtures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import save_manager
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram, habitability_weight

FIXTURES_DIR = ROOT / "web" / "tests" / "fixtures"
MAX_SEED_ATTEMPTS = 200


def _new_program(seed: int) -> ContactProgram:
    """A fresh offline program, past the 1977 decision (the fixtures load straight to the map)."""
    program = ContactProgram(seed=seed, offline=True, data_dir=ROOT / "data")
    program.drain_events()
    program.wow_signal.reply("")  # standard reply: puts wow.decided = True, matches new_game() + wow_reply
    program.drain_events()
    return program


def _write(program: ContactProgram, name: str) -> None:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    text = save_manager.serialize(program)
    out = FIXTURES_DIR / name
    out.write_text(text, encoding="utf-8")
    print(f"web/tests/fixtures/{name}: {len(text):,} bytes, generation {program.generation}")


def _force_living_civilization(system, stage: CivilizationStage, strategy: str) -> None:
    """Overwrite one system's rolled profile with a known one - the same fields `_roll_civilization`
    sets, just to fixed values instead of random ones, so the fixture is reproducible."""
    system.has_civilization = True
    system.is_extinct = False
    system.has_swan_song = False
    system.civilization_stage = stage
    system.civilization_age = 100.0
    system.civilization_type = "biological_pure"
    system.civilization_attitude = 0.5
    system.true_strategy = strategy
    system.deception_level = 0.1
    system.has_detected_earth = False
    system.knowledge = 30


# --------------------------------------------------------------------------- threat.json
def make_threat() -> None:
    """A hostile (LA) fleet launched in response to our own message, ETA >= 3 generations."""
    for seed in range(1, MAX_SEED_ATTEMPTS):
        program = _new_program(seed)
        system = next(iter(program.star_systems.values()))
        _force_living_civilization(system, CivilizationStage.DIGITAL, "LA")
        # A farther system gives the (slower-than-light) fleet a longer trip, comfortably past
        # the "ETA >= 3 generations" the plan asks for, whatever this seed's catalog looks like.
        system.distance = 30.0

        program.action_points = max(program.action_points, program.max_action_points, 1)
        program.send_message(system.name, "hello")
        program.drain_events()

        if program.pending_attack_warnings:
            warning = program.pending_attack_warnings[0]
            eta = warning.get_etas_remaining(program.generation)
            if eta >= 3:
                _write(program, "threat.json")
                return
    raise SystemExit("make_threat: could not build a fixture with ETA >= 3 within the seed budget")


# --------------------------------------------------------------------------- reply.json
def make_reply() -> None:
    """A system forced to LB with a reply already in flight (`pending_responses`)."""
    for seed in range(1, MAX_SEED_ATTEMPTS):
        program = _new_program(seed)
        system = next(iter(program.star_systems.values()))
        _force_living_civilization(system, CivilizationStage.DIGITAL, "LB")

        # LB's response is a 0.7-0.95 chance per message (game_interface parity, not a fixed
        # certainty), so retry with fresh Action Points until one lands rather than assume the
        # first call succeeds.
        for _ in range(30):
            if system.pending_responses:
                break
            program.action_points = max(program.action_points, 1)
            program.send_message(system.name, "hello")
            program.drain_events()

        if system.pending_responses:
            _write(program, "reply.json")
            return
    raise SystemExit("make_reply: no reply was queued within the seed/attempt budget")


# --------------------------------------------------------------------------- genesis.json
def make_genesis() -> None:
    """A Genesis ark launched and landed (`evolution_stage` >= 1: "Colony founded")."""
    for seed in range(1, MAX_SEED_ATTEMPTS):
        program = _new_program(seed)
        program.genesis.unlocked = True
        program.research_points = 10_000
        program.funding = 100.0
        program.action_points = max(program.action_points, program.max_action_points, 5)

        candidates = sorted(program.star_systems.values(), key=lambda s: s.distance)
        target = next(
            (s for s in candidates
             if not s.has_civilization and not getattr(s, "is_wow_source", False)
             and not s.is_seeded and habitability_weight(s.spectral_type) > 0),
            None,
        )
        if target is None:
            continue  # this seed's five starting systems left no sterile habitable world; try another
        # An ark only launches at a system the program has studied to 20% - the same thing
        # `focus_research` would have raised over a few generations, set directly here.
        target.knowledge = max(target.knowledge, 20)

        ok, message = program.genesis.seed_world(program, target)
        if not ok:
            continue
        program.drain_events()

        world = program.genesis.seeded_worlds[target.name]
        # Advance until the ark lands (evolution_stage 0 -> 1); answer any philosophical crisis
        # generically (choice 0) so it never blocks the loop - the fixture only cares about Genesis.
        for _ in range(50):
            if world.evolution_stage >= 1:
                break
            if program.pending_philosophical_event is not None:
                program.handle_philosophical_event_choice(0)
            program.advance_generation()
            program.drain_events()

        if world.evolution_stage >= 1:
            _write(program, "genesis.json")
            return
    raise SystemExit("make_genesis: no sterile habitable world was found/landed within the seed budget")


# --------------------------------------------------------------------------- gameover.json
def make_gameover() -> None:
    """A finished run: support collapsed and the program was defunded (`game_over`).

    Nothing is forced but the support figure the engine itself checks - drop it under the 10%
    floor `advance_generation` tests and let the engine end the run and write its own
    `game_over_reason`, exactly as a losing playthrough would.
    """
    for seed in range(1, MAX_SEED_ATTEMPTS):
        program = _new_program(seed)
        program.public_support = 5
        for _ in range(10):
            if program.game_over:
                break
            if program.pending_philosophical_event is not None:
                program.handle_philosophical_event_choice(0)
            program.public_support = min(program.public_support, 5)
            program.advance_generation()
            program.drain_events()

        if program.game_over:
            _write(program, "gameover.json")
            return
    raise SystemExit("make_gameover: the program never ended within the seed budget")


def main() -> None:
    make_threat()
    make_reply()
    make_genesis()
    make_gameover()


if __name__ == "__main__":
    main()
