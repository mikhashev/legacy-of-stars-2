"""
Offline narrative content for Legacy of Stars.

Alien replies, swan songs, WOW! signal texts and other written messages live in
data/templates/*.json and are filled with game context here.  The LLM, when
available, may replace them; the bank guarantees the game always has words.
"""
import json
import logging
import random
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
TEMPLATES_DIR = DATA_DIR / "templates"

GENERIC_REPLY = ("A transmission from {system} has arrived. Its structure is unmistakably artificial, "
                 "its content only partly decoded. Someone out there is answering.")
GENERIC_SWAN_SONG = ("[SIGNAL FRAGMENT] ... this is {system} ... we existed for {existence_duration} ... "
                     "remember us ... [SIGNAL LOST]")


class _SafeDict(dict):
    """Leaves unknown placeholders visible instead of raising KeyError."""

    def __missing__(self, key):
        return "{" + key + "}"


class ContentBank:
    """Loads template banks lazily and fills them with context."""

    def __init__(self, templates_dir: Path = TEMPLATES_DIR):
        self.templates_dir = Path(templates_dir)
        self._cache: Dict[str, dict] = {}

    # ------------------------------------------------------------------ plumbing
    def _load(self, name: str) -> dict:
        if name not in self._cache:
            path = self.templates_dir / f"{name}.json"
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._cache[name] = json.load(f)
            except (OSError, json.JSONDecodeError) as exc:
                logging.warning(f"Template bank '{name}' unavailable: {exc}")
                self._cache[name] = {}
        return self._cache[name]

    @staticmethod
    def fill(template: str, ctx: Optional[dict]) -> str:
        return template.format_map(_SafeDict(ctx or {}))

    def _pick(self, variants: Optional[List[str]], ctx: Optional[dict], fallback: str) -> str:
        if variants:
            return self.fill(random.choice(variants), ctx)
        return self.fill(fallback, ctx)

    # ------------------------------------------------------------------ banks
    def alien_reply(self, strategy: str, civ_type: Optional[str], ctx: Optional[dict] = None) -> str:
        """Reply from a living civilization. strategy: LB / LR / LBA; civ_type may be None."""
        data = self._load("alien_replies")
        block = data.get(strategy) or data.get("LR") or {}
        variants = block.get(civ_type or "any") or block.get("any")
        return self._pick(variants, ctx, GENERIC_REPLY)

    def swan_song(self, category: str, civ_type: Optional[str], ctx: Optional[dict] = None) -> str:
        """Final transmission of an extinct civilization."""
        data = self._load("swan_songs")
        text = self._pick(data.get(category), ctx, GENERIC_SWAN_SONG)
        if civ_type == "failed_transition":
            suffixes = data.get("failed_transition_suffix")
            if suffixes:
                text += "\n\n" + self.fill(random.choice(suffixes), ctx)
        return text

    def wow_friendly(self, ctx: Optional[dict] = None) -> str:
        data = self._load("wow_responses")
        return self._pick(data.get("friendly"), ctx,
                          "We heard you. Thirty-six centuries later, we are still glad you spoke.")

    def director_message(self, ctx: Optional[dict] = None) -> str:
        data = self._load("wow_responses")
        return self._pick(data.get("director_message"), ctx,
                          "Greetings from Earth. We heard your signal and we answer with hope.")

    def special(self, key: str, ctx: Optional[dict] = None) -> str:
        """Named one-off messages: mirror_friendly, mirror_hostile, genesis_greeting, genesis_hostile."""
        data = self._load("special_messages")
        return self._pick(data.get(key), ctx, "{system}: " + key.replace("_", " "))

    def mirror_reply(self, hostile: bool, ctx: Optional[dict] = None) -> str:
        return self.special("mirror_hostile" if hostile else "mirror_friendly", ctx)

    def genesis_greeting(self, ctx: Optional[dict] = None) -> str:
        return self.special("genesis_greeting", ctx)
