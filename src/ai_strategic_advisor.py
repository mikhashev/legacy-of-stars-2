"""
AI Strategic Advisor for Legacy of Stars
Provides context-aware strategic recommendations using AI
"""

import logging
from typing import Dict, List

class AIStrategicAdvisor:
    """Advanced AI that analyzes game state and provides strategic recommendations"""
    
    def __init__(self, ai_manager):
        self.ai_manager = ai_manager
        
    def analyze_game_state(self, program) -> str:
        """Main entry point - analyze current situation and provide recommendations"""
        
        # Build comprehensive context
        context = self._build_context(program)
        
        # Create strategic analysis prompt
        system_prompt = """You are Earth's Strategic AI Advisor for SETI operations in a Dark Forest universe.

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

        analysis_prompt = f"""Analyze the current game state and provide strategic recommendations:

{context}

Provide:
1. THREAT ASSESSMENT (current danger level)
2. SUSPICIOUS PATTERNS (systems to avoid/watch)
3. RECOMMENDED ACTIONS (what to do this generation)
4. LONG-TERM STRATEGY (next 3-5 generations)
5. FORECAST (predicted outcomes)

Keep each section brief (2-3 sentences max). Be direct and actionable."""

        # Generate strategic analysis
        try:
            advice = self.ai_manager.generate_text(analysis_prompt, system_prompt)
            return self._format_advice(advice, program)
        except Exception as e:
            logging.error(f"AI Advisor error: {e}")
            return self._fallback_analysis(program)
    
    def _build_context(self, program) -> str:
        """Build comprehensive game state context"""
        
        context_parts = []
        
        # Basic state
        current_year = program.start_year + ((program.generation - 1) * 25)
        context_parts.append(f"CURRENT STATE:")
        context_parts.append(f"Generation {program.generation} (Year {current_year})")
        context_parts.append(f"Action Points: {program.action_points}/{program.max_action_points}")
        context_parts.append(f"Public Support: {int(program.public_support)}%")
        context_parts.append(f"Funding: {int(program.funding)}%")
        context_parts.append(f"Knowledge Base: {int(program.knowledge_base)}%")
        context_parts.append(f"Research Points: {int(program.research_points)}")
        context_parts.append("")
        
        # Active threats
        if program.pending_attack_warnings:
            context_parts.append(f"ACTIVE THREATS: {len(program.pending_attack_warnings)}")
            for warning in program.pending_attack_warnings:
                etas = warning.get_etas_remaining(program.generation)
                defense = warning.get_defense_percentage()
                context_parts.append(f"  - {warning.source.name}: {etas} gens away, {defense}% defended")
            context_parts.append("")
        else:
            context_parts.append("ACTIVE THREATS: None")
            context_parts.append("")
        
        # Civilizations
        context_parts.append("KNOWN CIVILIZATIONS:")
        contacted_count = 0
        silent_sent = []
        friendly_responses = []
        extinct_found = []
        
        for name, system in program.star_systems.items():
            if not system.has_civilization:
                continue
                
            if system.is_extinct:
                extinct_found.append(name)
            elif len(system.received_messages) > 0:
                contacted_count += 1
                friendly_responses.append(name)
            elif len(system.messages_sent) > 0:
                silent_sent.append((name, len(system.messages_sent)))
        
        context_parts.append(f"  Contacted (friendly): {contacted_count}")
        if friendly_responses:
            context_parts.append(f"    {', '.join(friendly_responses)}")
        
        if silent_sent:
            context_parts.append(f"  Silent (messaged but no response): {len(silent_sent)}")
            for sys_name, msg_count in silent_sent[:3]:  # Top 3
                context_parts.append(f"    {sys_name} ({msg_count} messages sent, 0 received)")
        
        if extinct_found:
            context_parts.append(f"  Extinct: {len(extinct_found)}")
            context_parts.append(f"    {', '.join(extinct_found[:3])}")  # First 3
        
        context_parts.append("")
        
        # Risks
        context_parts.append("EXISTENTIAL RISKS:")
        context_parts.append(f"  Self-Destruct: {program.self_destruct_risk*100:.1f}%")
        context_parts.append(f"  Ecological: {program.ecological_risk*100:.1f}%")
        context_parts.append("")
        
        # Recent events (if we track them)
        if program.public_support < 30:
            context_parts.append("WARNING: Public support critically low!")
        if program.funding < 30:
            context_parts.append("WARNING: Funding critically low!")
        
        # Victory progress
        context_parts.append(f"\nVICTORY PROGRESS: {contacted_count}/3 contacts needed")
        
        return "\n".join(context_parts)
    
    def _format_advice(self, raw_advice: str, program) -> str:
        """Format AI advice for display"""
        
        header = f"""
{'='*60}
🤖 AI STRATEGIC BRIEFING - Generation {program.generation}
{'='*60}
"""
        
        footer = f"""
{'='*60}
End of briefing. Use this analysis to guide your decisions.
{'='*60}
"""
        
        return header + raw_advice + footer
    
    def _fallback_analysis(self, program) -> str:
        """Fallback analysis if AI generation fails"""
        
        # Simple rule-based analysis
        threats = len(program.pending_attack_warnings)
        support = program.public_support
        funding = program.funding
        contacted = sum(1 for s in program.star_systems.values() 
                       if s.has_civilization and len(s.received_messages) > 0)
        
        advice = f"""
{'='*60}
🤖 AI STRATEGIC BRIEFING - Generation {program.generation}
{'='*60}

THREAT ASSESSMENT:
"""
        
        if threats > 0:
            advice += f"⚠️ HIGH RISK - {threats} hostile fleet(s) incoming. Deploy defenses immediately.\n"
        else:
            advice += "✓ No active threats detected. Situation stable.\n"
        
        advice += "\nRESOURCE STATUS:\n"
        if support < 30:
            advice += "❌ CRITICAL: Public support dangerously low. Conduct outreach NOW.\n"
        elif support < 50:
            advice += "⚠️ WARNING: Public support declining. Consider outreach campaign.\n"
        else:
            advice += "✓ Public support adequate.\n"
        
        if funding < 30:
            advice += "❌ CRITICAL: Funding crisis. Boost support to restore funding.\n"
        elif funding < 50:
            advice += "⚠️ WARNING: Funding below optimal. Support restoration recommended.\n"
        
        advice += "\nRECOMMENDED ACTIONS:\n"
        if threats > 0:
            advice += "1. Deploy defensive measures against incoming threats\n"
        if support < 50:
            advice += "2. Public Outreach Campaign to restore support\n"
        if contacted < 3:
            advice += f"3. Continue contact efforts ({contacted}/3 needed for victory)\n"
        
        advice += f"""
\nVICTORY PROGRESS: {contacted}/3 contacts established

{'='*60}
AI Advisor analysis complete.
{'='*60}
"""
        
        return advice
    
    def get_system_risk_assessment(self, program, system_name: str) -> str:
        """Assess risk of a specific star system"""
        
        if system_name not in program.star_systems:
            return "System not found."
        
        system = program.star_systems[system_name]
        
        if not system.has_civilization:
            return f"{system_name}: No civilization detected. Low risk."
        
        if system.is_extinct:
            return f"{system_name}: Extinct civilization. No threat, may have data archives."
        
        messages_sent = len(system.messages_sent)
        messages_received = len(system.received_messages)
        
        if messages_received > 0:
            return f"{system_name}: Friendly contact established. Safe to continue communication."
        
        if messages_sent > 0:
            return f"{system_name}: ⚠️ SUSPICIOUS - {messages_sent} message(s) sent, NO response. Possible L or LA strategy. AVOID further contact."
        
        return f"{system_name}: Unknown. No contact attempted yet. Risk level unclear."
