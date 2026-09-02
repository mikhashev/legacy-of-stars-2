"""
Swan Song Messages - final transmissions from extinct civilizations.

Adds narrative depth and strategic intelligence to the Dark Forest game.
Message text is produced lazily, at discovery time: from the LLM when one is
available, otherwise from the offline template bank.
"""

import random
from enum import Enum
from typing import Dict, Optional

from .content import ContentBank


class SwanSongCategory(str, Enum):
    """Categories of swan song messages"""
    WARNING = "warning"
    ARCHIVE = "archive"
    TECHNICAL = "technical"
    PLEA = "plea"
    PHILOSOPHY = "philosophy"


CATEGORY_WEIGHTS = [
    (SwanSongCategory.WARNING, 0.30),      # Dark Forest warnings
    (SwanSongCategory.ARCHIVE, 0.25),      # Knowledge archives
    (SwanSongCategory.TECHNICAL, 0.20),    # Technical data
    (SwanSongCategory.PLEA, 0.15),         # Desperate pleas
    (SwanSongCategory.PHILOSOPHY, 0.10),   # Philosophical reflections
]

EXTINCTION_CONTEXT = {
    "warning": "They detected hostile contact and tried to warn others. They were destroyed by a Dark Forest predator.",
    "plea": "They were under attack and desperately called for help that never came.",
    "archive": "They knew their end was near (war/disaster/decay) and preserved their knowledge.",
    "technical": "They left behind technical schematics and research data before collapse.",
    "philosophy": "They reflected on existence, meaning, and their civilization's legacy before vanishing.",
}


def _category_value(category) -> str:
    return category.value if isinstance(category, Enum) else str(category)


class SwanSong:
    """Represents a final transmission from an extinct civilization"""

    def __init__(self, system_name: str, category, extinct_years_ago: int,
                 civ_age: float, civ_type: Optional[str] = None):
        self.system_name = system_name
        self.category = _category_value(category)
        self.extinct_years_ago = extinct_years_ago
        self.civ_age = civ_age
        self.civ_type = civ_type
        self.discovered = False
        self.message: Optional[str] = None
        self.rewards: Dict = {}
        self._calculate_rewards()

    # ------------------------------------------------------------------ text
    @property
    def existence_duration(self) -> str:
        if self.civ_age < 10000:
            return f"{int(self.civ_age)} years"
        return f"{int(self.civ_age / 1000)} thousand years"

    def _context(self) -> Dict:
        return {
            "system": self.system_name,
            "existence_duration": self.existence_duration,
            "extinct_years_ago": self.extinct_years_ago,
        }

    def _prompt(self) -> str:
        return f"""You are writing the final transmission (swan song) of an extinct alien civilization from {self.system_name}.

Context:
- They existed for {self.existence_duration}
- They went extinct {self.extinct_years_ago} years ago
- Message category: {self.category}
- Extinction circumstances: {EXTINCTION_CONTEXT.get(self.category, 'Unknown')}
- How they related to technology: {self.civ_type or 'unknown'}

Write a poignant, authentic final transmission (150-300 words) that:
1. Reflects their category ({self.category})
2. Feels like a real final message from a dying civilization
3. Provides useful insight or warning for Earth
4. Has emotional weight and philosophical depth
5. Is written from THEIR perspective (not about them)

Make it haunting, memorable, and meaningful. This is their last voice in the cosmos."""

    def ensure_message(self, ai=None, content: Optional[ContentBank] = None) -> str:
        """Produce the message text once (LLM if available, else the template bank)."""
        if self.message:
            return self.message
        text = None
        if ai is not None and ai.is_available():
            text = ai.generate_text("", self._prompt())
            if text and len(text.strip()) < 50:
                text = None
        if not text:
            bank = content or ContentBank()
            text = bank.swan_song(self.category, self.civ_type, self._context())
        self.message = text
        return text

    # ------------------------------------------------------------------ rewards
    def _calculate_rewards(self):
        """Calculate what the player receives for discovering this swan song"""
        if self.category == SwanSongCategory.WARNING:
            self.rewards = {
                "knowledge": 20,
                "research_points": 100,
                "public_support": -5,  # Scary revelation
                "message": "Dark Forest evidence... public fears grow.",
            }
        elif self.category == SwanSongCategory.ARCHIVE:
            self.rewards = {
                "knowledge": 30,
                "research_points": 150,
                "tech_hint": True,
                "message": "Vast knowledge archive recovered!",
            }
        elif self.category == SwanSongCategory.TECHNICAL:
            self.rewards = {
                "research_points": 250,
                "tech_discount": 0.25,  # 25% discount on next tech
                "message": "Technical schematics decoded! Research accelerated.",
            }
        elif self.category == SwanSongCategory.PLEA:
            self.rewards = {
                "knowledge": 15,
                "research_points": 50,
                "public_support": -10,  # Very disturbing
                "message": "Their desperation is... haunting. Public morale affected.",
            }
        else:  # PHILOSOPHY
            self.rewards = {
                "knowledge": 10,
                "public_support": 10,  # Inspirational
                "research_points": 75,
                "message": "Their wisdom inspires humanity. Public support increases.",
            }

        # Bonus for very old civilizations
        if self.civ_age > 100000:
            self.rewards["research_points"] = self.rewards.get("research_points", 0) + 100
            self.rewards["message"] += " (Ancient civilization bonus!)"

    def to_dict(self) -> Dict:
        return {
            "system_name": self.system_name,
            "category": self.category,
            "extinct_years_ago": self.extinct_years_ago,
            "civ_age": self.civ_age,
            "civ_type": self.civ_type,
            "discovered": self.discovered,
            "message": self.message,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "SwanSong":
        song = cls(data["system_name"], data["category"], data.get("extinct_years_ago", 0),
                   data.get("civ_age", 0.0), data.get("civ_type"))
        song.discovered = bool(data.get("discovered", False))
        song.message = data.get("message")
        return song

    def discover(self) -> Dict:
        """Mark as discovered and return rewards"""
        if self.discovered:
            return {"error": "Already discovered this swan song"}
        self.discovered = True
        return {
            "message": self.message or "",
            "rewards": self.rewards,
            "system": self.system_name,
            "category": self.category,
            "civ_type": self.civ_type,
        }


class SwanSongManager:
    """Manages swan song discovery mechanics"""

    def __init__(self, ai_manager=None, content: Optional[ContentBank] = None):
        self.ai = ai_manager
        self.content = content or ContentBank()
        self.swan_songs: Dict[str, SwanSong] = {}  # system_name -> SwanSong
        self.next_tech_discount = 0.0  # Accumulated tech discount

    def create_swan_song(self, system_name: str, extinct_years_ago: int, civ_age: float,
                         civ_type: Optional[str] = None) -> SwanSong:
        """Create a swan song for an extinct civilization (category chosen by weight)."""
        category = random.choices(
            [c for c, _ in CATEGORY_WEIGHTS],
            weights=[w for _, w in CATEGORY_WEIGHTS],
        )[0]
        swan_song = SwanSong(system_name, category, extinct_years_ago, civ_age, civ_type)
        self.swan_songs[system_name] = swan_song
        return swan_song

    def has_swan_song(self, system_name: str) -> bool:
        return system_name in self.swan_songs

    def is_discovered(self, system_name: str) -> bool:
        if system_name not in self.swan_songs:
            return False
        return self.swan_songs[system_name].discovered

    def discover_swan_song(self, system_name: str, system_knowledge: float) -> Dict:
        """Attempt to discover a swan song. Returns discovery results or an error dict."""
        if system_name not in self.swan_songs:
            return {"error": "No swan song exists for this system"}

        swan_song = self.swan_songs[system_name]
        if swan_song.discovered:
            return {"error": "Swan song already discovered"}

        # Minimum 30% knowledge required
        if system_knowledge < 30:
            return {"error": "Insufficient knowledge. Need 30%+ to detect artifacts."}

        # Discovery chance: 50% at 30 knowledge, 100% at 60+
        discovery_chance = min(1.0, (system_knowledge - 30) / 30 * 0.5 + 0.5)
        if random.random() > discovery_chance:
            return {"error": f"Deep scan in progress... ({int(discovery_chance * 100)}% detection probability)"}

        swan_song.ensure_message(self.ai, self.content)
        result = swan_song.discover()

        if "tech_discount" in result["rewards"]:
            self.next_tech_discount += result["rewards"]["tech_discount"]
        return result

    def get_tech_discount(self) -> float:
        """Get and consume the accumulated tech discount"""
        discount = self.next_tech_discount
        self.next_tech_discount = 0.0
        return discount

    def get_all_swan_songs_status(self) -> Dict[str, bool]:
        return {name: song.discovered for name, song in self.swan_songs.items()}

    def to_dict(self) -> Dict:
        return {
            "next_tech_discount": self.next_tech_discount,
            "swan_songs": [song.to_dict() for song in self.swan_songs.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict, ai_manager=None, content: Optional[ContentBank] = None) -> "SwanSongManager":
        manager = cls(ai_manager, content)
        manager.next_tech_discount = float(data.get("next_tech_discount", 0.0))
        for entry in data.get("swan_songs", []):
            song = SwanSong.from_dict(entry)
            manager.swan_songs[song.system_name] = song
        return manager
