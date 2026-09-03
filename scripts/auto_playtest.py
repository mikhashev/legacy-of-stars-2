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
    # "observer" spends three quarters of its action points on the sky and keeps a watch list
    # (see `study_target`); "talker" sends a message with almost every action point it has.
    #
    # T5 note: the observer's share was 0.60 and its studies picked a *uniformly random* system,
    # which is not an observatory - with 50-90 catalogued stars it never brought more than ~20 of
    # them past the 20 % knowledge the engine needs before it watches a star at all, so the
    # sky-change metric measured the harness's scattering rather than the sky. The mix below is
    # the policy T5 fixes: study, and study the same stars until they are on the watch list.
    "observer": (0.15, 0.05, 0.05, 0.75),
    "talker": (0.85, 0.05, 0.05, 0.05),
}
# Strategies that keep a watch list: they study the stars they have already begun to study, and
# only message a system on that list (or one that has already answered).
_CAREFUL_MESSAGE_STRATEGIES = {"observer"}
_WATCH_LIST_STRATEGIES = {"observer"}
# The knowledge at which a star counts as watched. It is the engine's own
# `OBSERVATION_KNOWLEDGE_REQUIRED`: below it nobody is pointing a telescope at that star from one
# generation to the next, so no sky change is ever noticed there.
OBSERVER_KNOWLEDGE_FLOOR = 20
# The distance that makes a one-way signal a multi-generation bet: 80 LY is more than three
# generations of light-time each way, so the director who sends will not read the answer.
FAR_SYSTEM_LY = 80.0
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
        # T4: the generation the deep sky first opened - the first star catalogued at or beyond
        # FAR_SYSTEM_LY. It measures the detection tiers, not luck: reach gating means a star
        # that far can only be drawn once the Detection tree has been pushed to tier 3.
        self.first_far_system_gen = None
        # T5 calibration (plan §7). The kinds of the sky changes in the order they were seen -
        # the first-impression metric asks whether one of the first three is a stage advance
        # rather than a death, so the order matters and the count alone does not.
        self.sky_change_kinds = []
        # The generation of the *first* sky-change event, for metric (g) - "first sky-change by
        # generation 10" - which is about how soon the sky reads as alive, not how often.
        self.first_sky_change_gen = None
        # The generation the first alien reply landed: the other first-impression metric.
        self.first_reply_gen = None
        # One entry per catalogued civilization, taken the generation its star is first
        # resolved: {"distance", "extinct"}. "extinct" is the *observed* frame - a death whose
        # light has already reached Earth - which is what "extinct at first observation" means.
        self.first_observations = []
        self._seen_systems = set()
        self._note_new_systems()

    def _note_new_systems(self) -> None:
        """Record the observed state of every star resolved since the last call (plan §7b).

        A star enters the catalogue at most once, so the first look at it is the only one this
        metric may use: `system.observed(year)` is the civilization as the light arriving now
        shows it, and a civilization whose death is already visible is "extinct at first
        observation". A civilization that has not been born yet in the light we receive is not
        extinct - it is simply not there - and counts as alive-so-far.
        """
        p = self.program
        for name, system in p.star_systems.items():
            if name in self._seen_systems:
                continue
            self._seen_systems.add(name)
            if not system.has_civilization or system.is_wow_source:
                continue
            if getattr(system, "timeline", None) is None:
                extinct = bool(system.is_extinct)          # an old save: the cached fields are all there is
            else:
                state = system.observed(p.current_year)
                extinct = (not state.alive) and state.died_year is not None
            self.first_observations.append(
                {"distance": float(system.distance), "extinct": bool(extinct)})

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
                    p.focus_research(self.study_target(systems))
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
                    p.focus_research(self.study_target(systems))
            else:
                p.focus_research(self.study_target(systems))

            if p.action_points == before:
                # Action was refused without spending AP; do something that always costs 1 AP.
                p.focus_research(self.study_target(systems))

    def study_target(self, systems):
        """Which system this profile points its telescopes at.

        Most profiles study at random, which is what a program with no observing plan does. The
        "observer" profile keeps a **watch list**: it finishes the star it has already begun -
        the one closest to the 20 % knowledge the engine needs before it notices anything at
        that star - and only then opens a new one, nearest first. Once every catalogued star is
        watched it deepens the least-known of them. This is the T5 measurement policy: the
        sky-change metric is about what a watchful program sees, so the instrument has to watch.
        """
        if self.strategy not in _WATCH_LIST_STRATEGIES:
            return random.choice(systems)
        p = self.program
        unwatched = [p.star_systems[name] for name in systems
                     if p.star_systems[name].knowledge < OBSERVER_KNOWLEDGE_FLOOR]
        if unwatched:
            return min(unwatched, key=lambda s: (-s.knowledge, s.distance)).name
        partial = [p.star_systems[name] for name in systems if p.star_systems[name].knowledge < 100]
        return min(partial, key=lambda s: s.knowledge).name if partial else random.choice(systems)

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
            self._note_new_systems()
            for event in p.drain_events():
                if event.kind == "sky_change":
                    self.sky_changes += 1
                    self.sky_change_kinds.append(event.data.get("change", "?"))
                    if self.first_sky_change_gen is None:
                        self.first_sky_change_gen = p.generation
                elif event.kind == "response_received" and self.first_reply_gen is None:
                    self.first_reply_gen = p.generation
                elif (event.kind == "system_discovered" and self.first_far_system_gen is None
                      and event.data.get("distance", 0) >= FAR_SYSTEM_LY):
                    self.first_far_system_gen = p.generation
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
            "sky_change_kinds": list(self.sky_change_kinds),
            "first_sky_change_gen": self.first_sky_change_gen,
            "first_reply_gen": self.first_reply_gen,
            "first_observations": list(self.first_observations),
            "first_far_system_gen": self.first_far_system_gen,
            "detection_reach_ly": p.detection_reach_ly(),
            "farthest_known_ly": max((s.distance for s in p.star_systems.values()
                                      if not s.is_wow_source), default=0.0),
            "systems_known": len(p.star_systems),
            "passive_detections": p.stats.get("passive_detections", 0),
            "info_attacks": p.stats.get("info_attacks", 0),
            "messages_sent": p.stats.get("messages_sent", 0),
            "message_fates": self.message_fates(),
            "exception": None,
        }


# ---------------------------------------------------------------------- calibration (T5, plan section 7)
# The distance bands the "extinct at first observation" share is reported in. Far stars are seen
# further in the past, so their band reads higher; one flat number would hide exactly that.
DISTANCE_BANDS = ((0.0, 20.0, "<=20 LY"), (20.0, 60.0, "20-60 LY"), (60.0, 160.0, "60-160 LY"))


def _median(values):
    """The median of a list of numbers, or None for an empty one."""
    ordered = sorted(values)
    if not ordered:
        return None
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2.0


def calibration_metrics(results) -> dict:
    """The plan section 7 calibration metrics over a batch of runs of one profile.

    Every number here is a target in the plan, and each is measured the same way every time:

    * ``extinct`` - the share of catalogued civilizations whose death was already visible the
      generation their star was first resolved, overall and per distance band (target 20-30 %);
    * ``sky_changes_per_40`` - sky changes normalised to a 40-generation game (target 3-6 for
      the "observer" profile, which is the one that studies the sky every generation and so is
      the only profile that watches enough systems for the number to mean anything);
    * ``differing_outcomes`` - the share of messages to an inhabited target whose outcome the
      receipt frame decided differently from a static evaluation, approximated as
      ``died_in_flight / (replied + silent + died_in_flight)`` (target 10-20 %);
    * ``victory_rate`` - contact or philosophical victories per game (target: within 20 % of
      the pre-timelines baseline);
    * ``first_reply_median`` - the median generation of the first reply (target: no later than
      the baseline);
    * ``stage_up_first_three`` - the share of games whose first three sky changes contain a
      stage advance rather than only deaths (the "the galaxy is alive" first impression);
    * ``first_sky_change_by_10`` - metric (g): the share of games whose *first* sky-change event
      happens at generation <= 10 (target >= 60 %) - a game with no sky change at all does not
      count;
    * ``non_death_first_three`` - metric (h): (f) reformulated - the share of games (of those
      with >= 3 sky changes) whose first three sky changes contain at least one that is *not*
      an extinction or a silence, i.e. is not a death (target >= 50 %). Broader than
      ``stage_up_first_three``: an "activity" change (new signals where the sky was quiet) also
      counts here, not only a stage advance.
    """
    results = [r for r in results if not r.get("exception")]
    games = len(results)
    bands = {label: {"civs": 0, "extinct": 0} for _, _, label in DISTANCE_BANDS}
    for result in results:
        for observation in result.get("first_observations") or []:
            for low, high, label in DISTANCE_BANDS:
                if low < observation["distance"] <= high or (low == 0.0 and observation["distance"] <= high):
                    bands[label]["civs"] += 1
                    bands[label]["extinct"] += bool(observation["extinct"])
                    break
    civs = sum(band["civs"] for band in bands.values())
    extinct = sum(band["extinct"] for band in bands.values())

    generations = sum(r["generations"] for r in results) or 1
    sky_changes = sum(r.get("sky_changes", 0) for r in results)

    fates = {}
    for result in results:
        for fate, count in (result.get("message_fates") or {}).items():
            fates[fate] = fates.get(fate, 0) + count
    inhabited = fates.get("replied", 0) + fates.get("silent", 0) + fates.get("died_in_flight", 0)

    wins = sum(1 for r in results if r["victory"] or r["philosophical_victory"])
    replies = [r["first_reply_gen"] for r in results if r.get("first_reply_gen") is not None]

    with_three = [r for r in results if len(r.get("sky_change_kinds") or []) >= 3]
    stage_up = sum(1 for r in with_three if "stage_up" in (r["sky_change_kinds"] or [])[:3])
    death_kinds = {"extinction", "silence"}
    non_death = sum(1 for r in with_three
                     if any(kind not in death_kinds for kind in (r["sky_change_kinds"] or [])[:3]))

    early_sky_change = sum(
        1 for r in results
        if r.get("first_sky_change_gen") is not None and r["first_sky_change_gen"] <= 10)

    return {
        "games": games,
        "civilizations_observed": civs,
        "extinct_share": (extinct / civs) if civs else None,
        "extinct_by_band": {
            label: {"civs": band["civs"], "extinct": band["extinct"],
                    "share": (band["extinct"] / band["civs"]) if band["civs"] else None}
            for label, band in bands.items()
        },
        "sky_changes": sky_changes,
        "sky_changes_per_game": sky_changes / games if games else 0.0,
        "sky_changes_per_40": 40.0 * sky_changes / generations,
        "message_fates": fates,
        "messages_to_inhabited": inhabited,
        "differing_outcomes": (fates.get("died_in_flight", 0) / inhabited) if inhabited else None,
        "victories": wins,
        "victory_rate": wins / games if games else 0.0,
        "first_reply_median": _median(replies),
        "games_with_a_reply": len(replies),
        "stage_up_first_three": (stage_up / len(with_three)) if with_three else None,
        "non_death_first_three": (non_death / len(with_three)) if with_three else None,
        "games_with_three_sky_changes": len(with_three),
        "games_below_three_sky_changes": games - len(with_three),
        "first_sky_change_by_10": (early_sky_change / games) if games else None,
        "games_with_a_sky_change": sum(1 for r in results if r.get("first_sky_change_gen") is not None),
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
                "sky_change_kinds": [], "first_sky_change_gen": None,
                "first_reply_gen": None, "first_observations": [],
                "systems_known": 0, "messages_sent": 0, "message_fates": {},
                "first_far_system_gen": None, "detection_reach_ly": 0.0, "farthest_known_ly": 0.0,
                "passive_detections": 0, "info_attacks": 0,
                "end_reason": f"EXCEPTION: {exc!r}", "exception": repr(exc),
            }
        results.append(result)

    print("\n=== PLAYTEST SUMMARY ===")
    print(f"{'Run':<4}{'Seed':<6}{'Strat':<11}{'Gen':<5}{'Win':<6}{'Integ':<7}{'Seed':<6}{'Cont':<6}"
          f"{'Swan':<6}{'Sky':<5}{'Sys':<5}{'Leak':<6}{'Info':<6}{'FarSys':<8}End reason")
    print("-" * 120)
    for r in results:
        win = "PHIL" if r["philosophical_victory"] else ("YES" if r["victory"] else "NO")
        print(
            f"{r['run_id']:<4}{r['seed']:<6}{r['strategy']:<11}{r['generations']:<5}{win:<6}"
            f"{r['integration_level']:<7.2f}{r['seeded_worlds']:<6}{r['contacts']:<6}"
            f"{r['swan_songs_found']:<6}{r.get('sky_changes', 0):<5}{r['systems_known']:<5}"
            f"{r['passive_detections']:<6}{r['info_attacks']:<6}"
            f"{str(r.get('first_far_system_gen') or '-'):<8}{r['end_reason'][:40]}"
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
    far_gens = sorted(r["first_far_system_gen"] for r in results
                      if r.get("first_far_system_gen") is not None)
    if far_gens:
        median = far_gens[len(far_gens) // 2] if len(far_gens) % 2 else (
            (far_gens[len(far_gens) // 2 - 1] + far_gens[len(far_gens) // 2]) / 2)
        print(f"First star at {FAR_SYSTEM_LY:.0f}+ LY: {len(far_gens)}/{len(results)} run(s) got one, "
              f"median generation {median}, range {far_gens[0]}-{far_gens[-1]}.")
    else:
        print(f"First star at {FAR_SYSTEM_LY:.0f}+ LY: none in {len(results)} run(s) - the "
              "Detection tree never opened that band.")
    reaches = [r.get("detection_reach_ly") for r in results if r.get("detection_reach_ly")]
    if reaches:
        print(f"  Final detection reach: {min(reaches):.0f}-{max(reaches):.0f} LY; farthest star "
              f"catalogued: {max(r.get('farthest_known_ly', 0.0) for r in results):.1f} LY.")
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
