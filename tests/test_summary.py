"""
Final report, score, help screen and system dossier.
"""
import contextlib
import io
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ.setdefault("LOS_OFFLINE", "1")

from src.game_interface import GameInterface  # noqa: E402
from src.legacy_of_stars_v3 import CivilizationStage, ContactProgram  # noqa: E402
from src.summary import build_summary, compute_score, score_breakdown  # noqa: E402
from src.ui_text import HELP_TEXT  # noqa: E402

SECTIONS = ("OUTCOME", "TIMELINE", "CONTACTS", "HOSTILE ENCOUNTERS", "TECHNOLOGY", "FERMI PARADOX EVIDENCE",
            "SWAN SONGS RECOVERED", "GENESIS PROJECT", "WOW! SIGNAL", "ACHIEVEMENTS", "SCORE")


def contacted(program, count):
    systems = list(program.star_systems.values())[:count]
    for system in systems:
        system.has_civilization = True
        system.is_extinct = False
        system.true_strategy = "LB"
        system.civilization_stage = CivilizationStage.DIGITAL
        system.received_messages.append("hello")
    return systems


class SummaryTest(unittest.TestCase):
    def test_summary_has_every_section_for_a_fresh_game(self):
        p = ContactProgram(seed=1, offline=True)
        text = build_summary(p)
        for section in SECTIONS:
            self.assertIn(section, text)
        self.assertIn("ONGOING", text)
        self.assertIn("No civilization ever answered", text)

    def test_score_grows_with_contacts_and_victories(self):
        p = ContactProgram(seed=1, offline=True)
        base = compute_score(p)
        contacted(p, 2)
        with_contacts = compute_score(p)
        self.assertEqual(with_contacts, base + 600)
        p.victory = True
        p.philosophical_victory = True
        self.assertEqual(compute_score(p), with_contacts + 5000)
        p.game_over = True
        p.game_over_reason = "Earth annihilated by the hostile fleet from Vega."
        self.assertEqual(compute_score(p), with_contacts + 4500)
        self.assertEqual(sum(score_breakdown(p).values()), compute_score(p))

    def test_summary_reveals_strategies_and_outcome(self):
        p = ContactProgram(seed=2, offline=True)
        systems = contacted(p, 1)
        systems[0].true_strategy = "LBA"
        p.wow_signal.stay_silent()
        p.game_over = True
        p.game_over_reason = "The contact program was defunded: public support collapsed."
        text = build_summary(p)
        self.assertIn("deceptive predator", text)
        self.assertIn("DEFEAT", text)
        self.assertIn("stayed silent", text)
        self.assertIn("Silent Wisdom", text)

    def test_summary_survives_a_loaded_program(self):
        p = ContactProgram(seed=3, offline=True)
        p2 = ContactProgram.from_dict(p.to_dict(), offline=True)
        self.assertEqual(build_summary(p2).count("\n"), build_summary(p).count("\n"))


class InterfaceExtrasTest(unittest.TestCase):
    def test_help_key_prints_rules(self):
        p = ContactProgram(seed=4, offline=True)
        ui = GameInterface(p)
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=[""]), contextlib.redirect_stdout(out):
            ui.dispatch("?", ui.build_menu())
        self.assertIn("HOW TO PLAY", out.getvalue())
        self.assertIn(HELP_TEXT.strip()[:40], out.getvalue())
        self.assertIn("offline", out.getvalue())

    def test_dossier_shows_messages_and_replies(self):
        p = ContactProgram(seed=4, offline=True)
        system = contacted(p, 1)[0]
        system.messages_sent.append(("Greetings from Earth", 1))
        ui = GameInterface(p)
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=["1", ""]), contextlib.redirect_stdout(out):
            ui.dispatch("v", ui.build_menu())
        text = out.getvalue()
        self.assertIn(f"DOSSIER: {system.name}", text)
        self.assertIn("Greetings from Earth", text)
        self.assertIn("hello", text)
        self.assertIn("RA", text)

    def test_ending_prints_final_report(self):
        p = ContactProgram(seed=4, offline=True)
        ui = GameInterface(p)
        out = io.StringIO()
        with mock.patch("builtins.input", side_effect=["", "6", "y", ""]), contextlib.redirect_stdout(out):
            ui.play()
        text = out.getvalue()
        self.assertIn("FINAL REPORT", text)
        self.assertIn("TOTAL", text)
        self.assertIn("closed the program", text)


if __name__ == "__main__":
    unittest.main()
