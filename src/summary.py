"""
End-of-game report and score for Legacy of Stars.

Pure functions over the engine state; the console prints the text, other
front-ends can use the same numbers.
"""
from typing import Dict, List

STRATEGY_REVEAL = {
    "L": "listener - never answered anyone",
    "LB": "broadcaster - friendly and open",
    "LR": "cautious responder",
    "LA": "silent aggressor",
    "LBA": "deceptive predator - friendly bait, then a fleet",
}

FERMI_LABELS = {
    "extinction_evidence": "Extinction cases",
    "dark_forest_evidence": "Hostile encounters",
    "cooperation_evidence": "Peaceful contacts",
    "great_filter_evidence": "Great Filter evidence",
}


def compute_score(program) -> int:
    """A single number for the legacy this program leaves behind."""
    researched = [t for t in program.technologies.values() if t.researched and not t.is_legacy]
    score = program.generation * 10
    score += len(program.contacted_systems()) * 300
    score += program.stats.get("swan_songs_found", 0) * 150
    score += sum(t.tier * 50 for t in researched)
    score += sum(program.fermi_evidence.values()) * 40
    score += int(program.integration.integration_level * 500)
    score += len(program.achievements) * 100
    if program.victory:
        score += 2000
    if program.philosophical_victory:
        score += 3000
    if "annihilated" in (program.game_over_reason or "").lower():
        score -= 500
    return max(0, score)


def score_breakdown(program) -> Dict[str, int]:
    researched = [t for t in program.technologies.values() if t.researched and not t.is_legacy]
    parts = {
        "Generations survived": program.generation * 10,
        "Civilizations contacted": len(program.contacted_systems()) * 300,
        "Swan songs recovered": program.stats.get("swan_songs_found", 0) * 150,
        "Technologies researched": sum(t.tier * 50 for t in researched),
        "Fermi evidence": sum(program.fermi_evidence.values()) * 40,
        "Integration progress": int(program.integration.integration_level * 500),
        "Achievements": len(program.achievements) * 100,
    }
    if program.victory:
        parts["Contact victory"] = 2000
    if program.philosophical_victory:
        parts["Philosophical victory"] = 3000
    if "annihilated" in (program.game_over_reason or "").lower():
        parts["Earth annihilated"] = -500
    return parts


def _outcome(program) -> str:
    if not program.game_over:
        return "ONGOING - the program is still active."
    reason = program.game_over_reason or "The program ended."
    if program.victory and program.philosophical_victory:
        return f"DOUBLE VICTORY - contact network and the Fermi answer. {reason}"
    if program.victory:
        return f"CONTACT VICTORY - humanity is no longer alone. {reason}"
    if program.philosophical_victory:
        return f"PHILOSOPHICAL VICTORY - the Fermi Paradox answered. {reason}"
    return f"DEFEAT - {reason}"


def build_summary(program) -> str:
    """The final report shown when a game ends (also usable at any time)."""
    year = program.start_year + (program.generation - 1) * 25
    line = "=" * 64
    out: List[str] = [line, "LEGACY OF STARS - FINAL REPORT", line, "", "OUTCOME", f"  {_outcome(program)}", ""]

    out.append("TIMELINE")
    out.append(f"  Generations: {program.generation} ({program.start_year} - {year})")
    out.append(f"  Directors who served: {len(program.directors)}")
    out.append(f"  Star systems catalogued: {len(program.star_systems)}")
    out.append("")

    contacted = program.contacted_systems()
    out.append(f"CONTACTS ({len(contacted)})")
    if contacted:
        for system in contacted:
            stage = system.civilization_stage.name.title() if system.civilization_stage else "unknown stage"
            strategy = STRATEGY_REVEAL.get(system.true_strategy, "unknown")
            out.append(f"  - {system.name}: {len(system.received_messages)} reply(ies), {stage}, revealed as {strategy}")
    else:
        out.append("  No civilization ever answered.")
    out.append("")

    stats = program.stats
    out.append("HOSTILE ENCOUNTERS")
    out.append(f"  Fleets launched at Earth: {stats.get('attacks_scheduled', 0)}  |  struck: {stats.get('attacks_landed', 0)}"
               f"  |  survived: {stats.get('attacks_survived', 0)}  |  information attacks: {stats.get('info_attacks', 0)}")
    if program.pending_attack_warnings:
        names = ", ".join(w.source.name for w in program.pending_attack_warnings)
        out.append(f"  Still inbound: {names}")
    out.append("")

    researched = [t for t in program.technologies.values() if t.researched and not t.is_legacy]
    by_tier: Dict[int, int] = {}
    for tech in researched:
        by_tier[tech.tier] = by_tier.get(tech.tier, 0) + 1
    tiers = ", ".join(f"T{tier}: {count}" for tier, count in sorted(by_tier.items())) or "none"
    out.append(f"TECHNOLOGY ({len(researched)} researched)")
    out.append(f"  By tier: {tiers}")
    if program.active_doctrines:
        out.append(f"  Doctrines: {', '.join(program.active_doctrines)}")
    status = program.integration.get_integration_status(program.generation)
    out.append(f"  Integration: {status['level']:.0%} - {status['status']}")
    out.append("")

    evidence = program.fermi_evidence
    out.append(f"FERMI PARADOX EVIDENCE ({sum(evidence.values())}/15)")
    for key, label in FERMI_LABELS.items():
        out.append(f"  {label}: {evidence.get(key, 0)}")
    out.append("")

    songs = [s for s in program.swan_song_manager.swan_songs.values() if s.discovered]
    out.append(f"SWAN SONGS RECOVERED ({len(songs)})")
    for song in songs:
        out.append(f"  - {song.system_name}: {song.category}")
    if not songs:
        out.append("  None.")
    out.append("")

    out.append("GENESIS PROJECT")
    out.append("  " + program.genesis.get_summary().replace("\n", "\n  "))
    out.append("")

    wow = program.wow_signal
    if not wow.decided:
        decision = "undecided"
    elif wow.wow_replied:
        decision = "replied in 1977"
        if wow.outcome:
            decision += f" - Generation 144 outcome: {wow.outcome}"
        elif program.generation < wow.wow_response_gen:
            decision += f" - the answer would have arrived in Generation {wow.wow_response_gen}"
    else:
        decision = "stayed silent in 1977 (-15% attack damage)"
    out.append("WOW! SIGNAL")
    out.append(f"  {decision}")
    out.append("")

    out.append(f"ACHIEVEMENTS ({len(program.achievements)})")
    out.append("  " + (", ".join(program.achievements) if program.achievements else "None."))
    out.append("")

    out.append("SCORE")
    for label, value in score_breakdown(program).items():
        out.append(f"  {label:<26}{value:>7}")
    out.append(f"  {'TOTAL':<26}{compute_score(program):>7}")
    out.append(line)
    return "\n".join(out)
