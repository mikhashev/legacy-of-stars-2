"""
AI Strategic Advisor for Legacy of Stars.

Provides context-aware strategic recommendations.  With an LLM available the
briefing is generated; otherwise (the default) a rule-based analyst produces it
from the same game state.  Both paths read only what the player can see.
"""

import logging
from typing import List


class AIStrategicAdvisor:
    """Analyzes game state and provides strategic recommendations"""

    SYSTEM_PROMPT = """You are Earth's Strategic AI Advisor for SETI operations in a Dark Forest universe.

Your role:
- Analyze threats and opportunities
- Identify suspicious patterns
- Recommend specific actions
- Forecast long-term consequences

Remember:
- Dark Forest theory: Silence may indicate hostility (LA strategy)
- Not all civilizations are friendly (LA/LBA exist)
- Light-speed delays mean attacks take generations to arrive
- Resource management is critical (AP, support, funding)

Be concise, actionable, and strategic. Format your response with clear sections."""

    def __init__(self, ai_manager=None):
        self.ai_manager = ai_manager

    # ------------------------------------------------------------------ entry point
    def analyze_game_state(self, program) -> str:
        """Analyze the current situation and provide recommendations."""
        if self.ai_manager is not None and self.ai_manager.is_available():
            context = self._build_context(program)
            analysis_prompt = f"""Analyze the current game state and provide strategic recommendations:

{context}

Provide:
1. THREAT ASSESSMENT (current danger level)
2. SUSPICIOUS PATTERNS (systems to avoid/watch)
3. RECOMMENDED ACTIONS (what to do this generation)
4. LONG-TERM STRATEGY (next 3-5 generations)
5. FORECAST (predicted outcomes)

Keep each section brief (2-3 sentences max). Be direct and actionable."""
            try:
                advice = self.ai_manager.generate_text(analysis_prompt, self.SYSTEM_PROMPT)
            except Exception as exc:  # noqa: BLE001 - advisor must always answer
                logging.error(f"AI Advisor error: {exc}")
                advice = None
            if advice:
                return self._format_advice(advice, program)
        return self._rule_based_briefing(program)

    # ------------------------------------------------------------------ context
    @staticmethod
    def _contacted(program) -> List[str]:
        return [name for name, s in program.star_systems.items()
                if s.has_civilization and not s.is_extinct and len(s.received_messages) > 0]

    def _build_context(self, program) -> str:
        """Build the game-state context for the LLM (player-visible information only)."""
        parts = []
        current_year = program.start_year + ((program.generation - 1) * 25)
        parts.append("CURRENT STATE:")
        parts.append(f"Generation {program.generation} (Year {current_year})")
        parts.append(f"Action Points: {program.action_points}/{program.max_action_points}")
        parts.append(f"Public Support: {int(program.public_support)}%")
        parts.append(f"Funding: {int(program.funding)}%")
        parts.append(f"Knowledge Base: {int(program.knowledge_base)}%")
        parts.append(f"Research Points: {int(program.research_points)}")
        parts.append(f"Tech Level: {program.tech_level}")
        parts.append("")

        if program.pending_attack_warnings:
            parts.append(f"ACTIVE THREATS: {len(program.pending_attack_warnings)}")
            for warning in program.pending_attack_warnings:
                etas = warning.get_etas_remaining(program.generation)
                parts.append(f"  - {warning.source.name}: {etas} gens away, {warning.get_defense_percentage()}% defended")
        else:
            parts.append("ACTIVE THREATS: None")
        parts.append("")

        contacted = self._contacted(program)
        silent = [(n, len(s.messages_sent)) for n, s in program.star_systems.items()
                  if s.has_civilization and not s.is_extinct and s.messages_sent and not s.received_messages]
        extinct = [n for n, s in program.star_systems.items() if s.has_civilization and s.is_extinct and s.knowledge >= 20]
        parts.append("KNOWN CIVILIZATIONS:")
        parts.append(f"  Contacted (responded): {len(contacted)} {', '.join(contacted)}")
        if silent:
            parts.append(f"  Silent (messaged, no response): {len(silent)}")
            for name, count in silent[:3]:
                parts.append(f"    {name} ({count} messages sent, 0 received)")
        if extinct:
            parts.append(f"  Extinct: {', '.join(extinct[:3])}")
        parts.append("")
        parts.append("EXISTENTIAL RISKS:")
        parts.append(f"  Self-Destruct: {program.self_destruct_risk * 100:.1f}%")
        parts.append(f"  Ecological: {program.ecological_risk * 100:.1f}%")
        parts.append(f"  Integration: {program.integration.integration_level:.0%}")
        parts.append("")
        if program.public_support < 30:
            parts.append("WARNING: Public support critically low!")
        if program.funding < 30:
            parts.append("WARNING: Funding critically low!")
        total_evidence = sum(program.fermi_evidence.values())
        parts.append(f"\nVICTORY PROGRESS: {len(contacted)}/3 contacts, {total_evidence}/15 Fermi evidence")
        return "\n".join(parts)

    def _format_advice(self, raw_advice: str, program) -> str:
        header = f"\n{'=' * 60}\n🤖 AI STRATEGIC BRIEFING - Generation {program.generation}\n{'=' * 60}\n"
        footer = f"\n{'=' * 60}\nEnd of briefing. Use this analysis to guide your decisions.\n{'=' * 60}\n"
        return header + raw_advice + footer

    # ------------------------------------------------------------------ rule-based analyst
    def _rule_based_briefing(self, program) -> str:
        """Deterministic analysis of the visible game state."""
        gen = program.generation
        threats = program.pending_attack_warnings
        support = program.public_support
        funding = program.funding
        contacted = self._contacted(program)
        lines = [f"\n{'=' * 60}", f"🤖 AI STRATEGIC BRIEFING - Generation {gen}", f"{'=' * 60}", ""]

        # Threats
        lines.append("THREAT ASSESSMENT:")
        if threats:
            for warning in threats:
                etas = warning.get_etas_remaining(gen)
                defended = warning.get_defense_percentage()
                urgency = "IMMINENT" if etas <= 1 else ("HIGH" if etas <= 3 else "TRACKED")
                lines.append(f"  ⚠️ {urgency}: {warning.type_label} from {warning.source.name} - "
                             f"ETA {etas} gen(s), {defended}% defended")
            if any(w.get_defense_percentage() == 0 for w in threats):
                lines.append("  → Deploy Evacuation or the Emergency Defense Protocol before arrival.")
        else:
            front = program.leakage_system.leakage_front(
                program.start_year + (program.generation - 1) * 25)
            lines.append("  ✓ No hostile fleets detected. Our leakage front has already passed "
                         f"{front:.0f} LY.")
        lines.append("")

        # Resources
        lines.append("RESOURCE STATUS:")
        if support < 30:
            lines.append("  ❌ CRITICAL: Public support dangerously low. Conduct outreach NOW.")
        elif support < 50:
            lines.append("  ⚠️ Public support declining. Schedule an outreach campaign.")
        else:
            lines.append("  ✓ Public support adequate.")
        if funding < 30:
            lines.append("  ❌ CRITICAL: Funding crisis. Support drives funding; restore it first.")
        elif funding < 50:
            lines.append("  ⚠️ Funding below optimal.")
        else:
            lines.append("  ✓ Funding stable.")
        affordable = [t for t in program.available_technologies() if program.research_points >= t.cost]
        if affordable:
            names = ", ".join(t.name for t in affordable[:3])
            lines.append(f"  💡 Research available now: {names}")
        lines.append("")

        # Systems
        lines.append("SYSTEM NOTES:")
        noted = 0
        for name, system in program.star_systems.items():
            if system.messages_sent or system.knowledge > 0:
                lines.append(f"  - {self.get_system_risk_assessment(program, name)}")
                noted += 1
            if noted >= 6:
                break
        if not noted:
            lines.append("  - No systems studied yet. Focus Research reveals who is out there.")
        lines.append("")

        # Integration
        level = program.integration.integration_level
        if gen <= 30:
            lines.append(f"INTEGRATION: {level:.0%} - grace period until Generation 30, "
                         "then low integration will cost support and raise self-destruct risk.")
        elif level < 0.3:
            lines.append(f"INTEGRATION: {level:.0%} - CRISIS. Research Transcendence technologies "
                         "(Bio-Engineering → Synthetic Biology / Neural Interface).")
        else:
            lines.append(f"INTEGRATION: {level:.0%} - transition under way.")
        lines.append("")

        # Recommendations
        lines.append("RECOMMENDED ACTIONS:")
        recs = []
        if threats and any(w.get_defense_percentage() < 50 for w in threats):
            recs.append("Defend against incoming fleets (Defensive Actions).")
        if support < 50:
            recs.append("Public Outreach to restore support.")
        if program.undiscovered_swan_songs():
            recs.append("Study extinct systems to 30%+ knowledge, then listen for their swan songs.")
        unknown = [n for n, s in program.star_systems.items() if s.knowledge < 20]
        if unknown:
            recs.append(f"Focus Research on unstudied systems ({unknown[0]} first).")
        if len(contacted) < 3:
            recs.append("Message civilizations that already responded; each reply is safe evidence of cooperation.")
        if not recs:
            recs.append("Position is stable. Invest research points in detection and defense technologies.")
        for i, rec in enumerate(recs, 1):
            lines.append(f"  {i}. {rec}")
        lines.append("")

        total_evidence = sum(program.fermi_evidence.values())
        lines.append(f"VICTORY PROGRESS: {len(contacted)}/3 contacts | Fermi evidence {total_evidence}/15")
        lines.append(f"{'=' * 60}")
        lines.append("AI Advisor analysis complete.")
        lines.append(f"{'=' * 60}")
        return "\n".join(lines)

    def get_system_risk_assessment(self, program, system_name: str) -> str:
        """Assess the risk of a specific star system from visible evidence only."""
        if system_name not in program.star_systems:
            return "System not found."
        system = program.star_systems[system_name]

        if system.knowledge >= 20 and not system.has_civilization:
            return f"{system_name}: No civilization detected. Low risk; candidate for the Genesis Project."
        if system.knowledge >= 20 and system.is_extinct:
            hint = " Archives likely - listen for a swan song." if system.has_swan_song and system.knowledge >= 60 else ""
            return f"{system_name}: Extinct civilization. No threat.{hint}"

        sent = len(system.messages_sent)
        received = len(system.received_messages)
        if received > 0:
            return f"{system_name}: Responded to {received} message(s). Contact established; verify intentions before sharing more."
        if sent > 0:
            return (f"{system_name}: ⚠️ SUSPICIOUS - {sent} message(s) sent, none answered. "
                    "Silence may mean a listener-only civilization... or a hostile one. Avoid further contact.")
        if system.knowledge >= 20:
            return f"{system_name}: Civilization detected, not yet contacted. Study before speaking."
        return f"{system_name}: Unknown. Knowledge {int(system.knowledge)}%. Risk level unclear."
