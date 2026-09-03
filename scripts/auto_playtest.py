"""
Headless automated playtest harness for Legacy of Stars.

Runs complete games without a UI and reports how each one ended.  Used both
as a CLI smoke test and from the unit tests (tests/test_smoke.py).

    python scripts/auto_playtest.py --runs 5 --seed 1 --max-gen 200
    python scripts/auto_playtest.py --strategy aggressive

Importable API:
    run_headless(seed, strategy="balanced", max_gen=200) -> dict
"""
import argparse
import logging
import os
import random
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# The harness never talks to an LLM.
os.environ.setdefault("LOS_OFFLINE", "1")

from src.legacy_of_stars_v3 import ContactProgram  # noqa: E402

STRATEGIES = ("balanced", "aggressive", "cautious", "integration", "neglect", "observer", "talker")

# Probability weights per strategy: (send message, outreach, swan song, focus research)
_AP_WEIGHTS = {
    "balanced": (0.40, 0.30, 0.10, 0.20),
    "aggressive": (0.60, 0.15, 0.10, 0.15),
    "cautious": (0.15, 0.45, 0.15, 0.25),
    # "integration" plays the intended long game: Transcendence research first, careful messaging
    "integration": (0.25, 0.40, 0.15, 0.20),
    # "neglect" ignores the biological-technological transition entirely (never researches Transcendence)
    "neglect": (0.30, 0.40, 0.10, 0.20),
    # The two measurement profiles the plan fixes (§7a), so the receipt-frame numbers below are
    # reproducible rather than a by-product of whatever the mixed rotation happened to do:
    # "observer" studies the sky every generation and only ever writes to a system it already
    # knows something about; "talker" sends a message with almost every action point it has.
    "observer": (0.10, 0.20, 0.10, 0.60),
    "talker": (0.85, 0.05, 0.05, 0.05),
}
# Strategies that only message a system they have reason to trust: one that already answered, or
# one studied past this knowledge floor. Everything else gets studied instead.
_CAREFUL_MESSAGE_STRATEGIES = {"observer"}
OBSERVER_KNOWLEDGE_FLOOR = 40
_PRIORITY_CATEGORIES = {"integration": ("Transcendence", "Computing", "Social")}
_SKIPPED_CATEGORIES = {"neglect": ("Transcendence",)}


class AutoPlayer:
    """A scripted player that spends every action point each generation."""

    def __init__(self, run_id: int, strategy: str = "balanced", seed=None, max_gen: int = 200):
        if strategy not in _AP_WEIGHTS:
            raise ValueError(f"Unknown strategy {strategy!r}; choose from {STRATEGIES}")
        self.run_id = run_id
        self.strategy = strategy
        self.seed = seed
        self.max_gen = max_gen
        self.program = ContactProgram(seed=seed, offline=True)
        self.logs = []
        # Sky changes seen during the run (T1): new light showing a watched system advance a
        # stage or fall silent. Counted from the event stream, which nothing else here reads.
        self.sky_changes = 0

    def log(self, msg: str) -> None:
        self.logs.append(f"[Gen {self.program.generation}] {msg}")
        logging.info(f"[Run {self.run_id}] {msg}")

    # ------------------------------------------------------------------ turn
    def make_decisions(self) -> None:
        p = self.program
        systems = list(p.star_systems.keys())

        # 1. Defend against imminent attacks.
        for i, warning in enumerate(list(p.pending_attack_warnings)):
            if warning.get_etas_remaining(p.generation) > 2:
                continue
            if (p.action_points == p.max_action_points
                    and "Emergency Defense Protocol" not in warning.defensive_actions_taken):
                p.defend_emergency(i)
                self.log(f"Emergency Defense against {warning.source.name}")
            elif p.action_points >= 1 and "Evacuation" not in warning.defensive_actions_taken:
                p.defend_evacuate(i)
                self.log(f"Evacuation against {warning.source.name}")

        # 2. Genesis seeding when rich.
        if p.genesis.unlocked and len(p.genesis.seeded_worlds) < 2 \
                and p.research_points > 600 and p.funding > 40:
            # `genesis_targets()`'s own conditions: an ark only launches at a world the
            # program has actually studied (20% knowledge), which is also all the player
            # is offered in the console and web pickers.
            sterile = [p.star_systems[name] for name in p.genesis_targets()]
            if sterile:
                target = random.choice(sterile)
                success, _ = p.genesis.seed_world(p, target)
                if success:
                    self.log(f"Seeded life on {target.name}")

        # 3. Research the cheapest affordable technologies.
        available = [
            t for t in p.technologies.values()
            if not t.researched
            and p.generation >= t.min_generation
            and all(p.technologies[q].researched for q in t.prerequisites if q in p.technologies)
        ]
        priority = _PRIORITY_CATEGORIES.get(self.strategy, ())
        skipped = _SKIPPED_CATEGORIES.get(self.strategy, ())
        available = [t for t in available if t.category not in skipped]
        available.sort(key=lambda t: (t.category not in priority, t.cost))
        for tech in available:
            if p.tech_lock_reason(tech):
                continue
            if p.research_points >= tech.cost:
                needs_choice = p.research_tech(tech.id)
                if tech.researched:
                    self.log(f"Researched {tech.name}")
                if needs_choice and tech.doctrine_choice:
                    p.choose_doctrine(tech.id, 0)
                    self.log(f"Doctrine option 0 for {tech.name}")

        # 4. Spend the remaining action points.
        msg_w, outreach_w, swan_w, _ = _AP_WEIGHTS[self.strategy]
        guard = 0
        while p.action_points > 0 and guard < 25:
            guard += 1
            before = p.action_points
            roll = random.random()
            if roll < msg_w:
                target = self.pick_message_target(systems)
                if target is None:
                    p.focus_research(random.choice(systems))
                else:
                    p.send_message(target, "Greetings from Earth. We seek peaceful contact.")
                    self.log(f"Message sent to {target}")
            elif roll < msg_w + outreach_w:
                p.public_outreach()
            elif roll < msg_w + outreach_w + swan_w:
                # Only what a player can see: systems already studied to 20 % and known to be
                # extinct. With none, study instead - that is how the list gets populated.
                candidates = p.swan_song_targets()
                if candidates:
                    target = random.choice(candidates)
                    p.listen_for_swan_song(target)
                    self.log(f"Listened for swan song at {target}")
                else:
                    p.focus_research(random.choice(systems))
            else:
                p.focus_research(random.choice(systems))

            if p.action_points == before:
                # Action was refused without spending AP; do something that always costs 1 AP.
                p.focus_research(random.choice(systems))

    def pick_message_target(self, systems):
        """Which system this profile is willing to write to.

        Most profiles shout at anything in the catalogue. "observer" does not: it writes only to
        a civilization that has already answered, or one it has studied past
        `OBSERVER_KNOWLEDGE_FLOOR` - the cautious play the plan asks the metrics to be measured
        against. With no such target it has nothing to say, and studies instead.
        """
        if self.strategy not in _CAREFUL_MESSAGE_STRATEGIES:
            return random.choice(systems)
        known = [name for name in systems
                 if self.program.star_systems[name].received_messages
                 or self.program.star_systems[name].knowledge >= OBSERVER_KNOWLEDGE_FLOOR]
        return random.choice(known) if known else None

    def message_fates(self) -> dict:
        """How every message this game sent turned out (plan §7c).

        These are the engine's hidden fates, not the player's view: "died in flight" is exactly
        the outcome no director ever gets told at the time, and counting it is the only way to
        measure how often the receipt frame decided something a static evaluation would not have.
        """
        counts = {"in_flight": 0, "replied": 0, "nobody": 0, "died_in_flight": 0, "silent": 0}
        for system in self.program.star_systems.values():
            for entry in system.messages_sent:
                fate = entry.get("fate", "in_flight") if isinstance(entry, dict) else "in_flight"
                counts[fate] = counts.get(fate, 0) + 1
        return counts

    def resolve_pending_event(self) -> None:
        """Answer a pending philosophical event at random so it never blocks the run."""
        p = self.program
        event = p.pending_philosophical_event
        if event is not None:
            choice = random.randrange(len(event.choices))
            p.handle_philosophical_event_choice(choice)
            self.log(f"Philosophical event {event.name}: option {choice}")

    # ------------------------------------------------------------------ game
    def run(self) -> dict:
        p = self.program
        while not p.game_over and p.generation < self.max_gen:
            self.resolve_pending_event()
            self.make_decisions()
            p.advance_generation()
            self.sky_changes += sum(1 for event in p.drain_events() if event.kind == "sky_change")
            if p.generation % 20 == 0:
                status = p.integration.get_integration_status(p.generation)
                self.log(
                    f"Gen {p.generation} stats: integ={status['level']:.2f} "
                    f"risk={p.self_destruct_risk:.3f} support={p.public_support:.1f}"
                )
        return self.summary()

    def summary(self) -> dict:
        p = self.program
        status = p.integration.get_integration_status(p.generation)
        contacts = [
            name for name, s in p.star_systems.items()
            if s.has_civilization and len(s.received_messages) > 0
        ]
        swan_found = sum(
            1 for name, s in p.star_systems.items()
            if s.has_civilization and s.is_extinct and p.swan_song_manager.is_discovered(name)
        )
        end_reason = getattr(p, "game_over_reason", "") or (p.message or "").strip().split("\n")[0]
        if not p.game_over:
            end_reason = f"Reached generation cap ({self.max_gen})"
        return {
            "run_id": self.run_id,
            "seed": self.seed,
            "strategy": self.strategy,
            "generations": p.generation,
            "victory": p.victory,
            "philosophical_victory": p.philosophical_victory,
            "end_reason": end_reason,
            "integration_level": status["level"],
            "integration_status": status["status"],
            "tech_level": p.tech_level,
            "seeded_worlds": len(p.genesis.seeded_worlds),
            "contacts": len(contacts),
            "contact_names": contacts,
            "swan_songs_found": swan_found,
            "sky_changes": self.sky_changes,
            "systems_known": len(p.star_systems),
            "passive_detections": p.stats.get("passive_detections", 0),
            "info_attacks": p.stats.get("info_attacks", 0),
            "messages_sent": p.stats.get("messages_sent", 0),
            "message_fates": self.message_fates(),
            "exception": None,
        }


def format_fates(counts: dict) -> str:
    """The fate tally as one line: "replied 4, silent 9, nobody 21, died in flight 2"."""
    if not counts:
        return "none"
    order = ("replied", "in_flight", "silent", "nobody", "died_in_flight")
    parts = [f"{fate.replace('_', ' ')} {counts[fate]}" for fate in order if counts.get(fate)]
    return ", ".join(parts) or "none"


def run_headless(seed=None, strategy: str = "balanced", max_gen: int = 200, run_id: int = 1) -> dict:
    """Play one complete game without a UI and return its summary dict."""
    return AutoPlayer(run_id, strategy, seed=seed, max_gen=max_gen).run()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Headless playtest for Legacy of Stars")
    parser.add_argument("--runs", type=int, default=5, help="number of games to play (default 5)")
    parser.add_argument("--seed", type=int, default=1, help="seed of the first run; run i uses seed+i")
    parser.add_argument("--max-gen", type=int, default=200, help="generation cap per game")
    parser.add_argument("--strategy", choices=STRATEGIES + ("mixed",), default="mixed",
                        help="player strategy (default: cycle through all)")
    args = parser.parse_args(argv)

    os.makedirs(ROOT / "logs", exist_ok=True)
    logging.basicConfig(
        filename=str(ROOT / "logs" / "auto_playtest.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        filemode="w",
        encoding="utf-8",
    )

    print(f"\n=== AUTOMATED PLAYTEST: {args.runs} run(s), seed {args.seed}+, cap {args.max_gen} gens ===\n")
    results = []
    failures = 0
    for i in range(args.runs):
        seed = args.seed + i
        strategy = STRATEGIES[i % len(STRATEGIES)] if args.strategy == "mixed" else args.strategy
        print(f"Run {i + 1} ({strategy}, seed {seed})...", flush=True)
        try:
            result = run_headless(seed, strategy, args.max_gen, run_id=i + 1)
            print(f"  -> Gen {result['generations']}: {result['end_reason']}")
            print(f"     messages {result['messages_sent']}: {format_fates(result['message_fates'])}")
        except Exception as exc:  # noqa: BLE001 - report and keep going
            failures += 1
            traceback.print_exc()
            result = {
                "run_id": i + 1, "seed": seed, "strategy": strategy, "generations": "?",
                "victory": False, "philosophical_victory": False, "integration_level": 0.0,
                "seeded_worlds": 0, "contacts": 0, "swan_songs_found": 0, "sky_changes": 0,
                "systems_known": 0, "messages_sent": 0, "message_fates": {},
                "passive_detections": 0, "info_attacks": 0,
                "end_reason": f"EXCEPTION: {exc!r}", "exception": repr(exc),
            }
        results.append(result)

    print("\n=== PLAYTEST SUMMARY ===")
    print(f"{'Run':<4}{'Seed':<6}{'Strat':<11}{'Gen':<5}{'Win':<6}{'Integ':<7}{'Seed':<6}{'Cont':<6}"
          f"{'Swan':<6}{'Sky':<5}{'Sys':<5}{'Leak':<6}{'Info':<6}End reason")
    print("-" * 110)
    for r in results:
        win = "PHIL" if r["philosophical_victory"] else ("YES" if r["victory"] else "NO")
        print(
            f"{r['run_id']:<4}{r['seed']:<6}{r['strategy']:<11}{r['generations']:<5}{win:<6}"
            f"{r['integration_level']:<7.2f}{r['seeded_worlds']:<6}{r['contacts']:<6}"
            f"{r['swan_songs_found']:<6}{r.get('sky_changes', 0):<5}{r['systems_known']:<5}"
            f"{r['passive_detections']:<6}{r['info_attacks']:<6}{r['end_reason'][:45]}"
        )
    total_leak = sum(r["passive_detections"] for r in results)
    total_info = sum(r["info_attacks"] for r in results)
    total_sky = sum(r.get("sky_changes", 0) for r in results)
    print(f"\nPassive detections: {total_leak} total, {total_leak / max(1, len(results)):.2f} per game. "
          f"Information attacks: {total_info} total, {total_info / max(1, len(results)):.2f} per game.")
    print(f"Sky changes (new light showing a watched system change): {total_sky} total, "
          f"{total_sky / max(1, len(results)):.2f} per game.")
    totals = {}
    for r in results:
        for fate, count in (r.get("message_fates") or {}).items():
            totals[fate] = totals.get(fate, 0) + count
    sent = sum(totals.values())
    print(f"Message fates over {sent} message(s): {format_fates(totals)}")
    if sent:
        decided_by_the_future = totals.get("died_in_flight", 0)
        print(f"  Decided by the receipt frame (target gone before our signal landed): "
              f"{decided_by_the_future} ({decided_by_the_future / sent:.1%}).")
    if failures:
        print(f"\n{failures} run(s) raised exceptions.")
        return 1
    print("\nAll runs completed without exceptions.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
