"""
Swan Song Messages - Final transmissions from extinct civilizations
Adds narrative depth and strategic intelligence to the Dark Forest game
"""

import random
from typing import Dict, Optional
from ai_manager import AIManager

class SwanSongCategory:
    """Categories of swan song messages"""
    WARNING = "warning"
    ARCHIVE = "archive"
    TECHNICAL = "technical"
    PLEA = "plea"
    PHILOSOPHY = "philosophy"

class SwanSong:
    """Represents a final transmission from an extinct civilization"""
    
    def __init__(self, system_name: str, category: str, extinct_years_ago: int, 
                 civ_age: float, ai_manager: AIManager):
        self.system_name = system_name
        self.category = category
        self.extinct_years_ago = extinct_years_ago
        self.civ_age = civ_age
        self.discovered = False
        self.message = None
        self.rewards = {}
        self.ai = ai_manager
        
        # Generate message content when created (but only revealed when discovered)
        self._generate_message()
        self._calculate_rewards()
    
    def _generate_message(self):
        """Generate AI-based swan song message based on category"""
        
        # Determine extinction cause probability based on category
        causes = {
            SwanSongCategory.WARNING: "They detected hostile contact and tried to warn others. They were destroyed by a Dark Forest predator.",
            SwanSongCategory.PLEA: "They were under attack and desperately called for help that never came.",
            SwanSongCategory.ARCHIVE: "They knew their end was near (war/disaster/decay) and preserved their knowledge.",
            SwanSongCategory.TECHNICAL: "They left behind technical schematics and research data before collapse.",
            SwanSongCategory.PHILOSOPHY: "They reflected on existence, meaning, and their civilization's legacy before vanishing."
        }
        
        extinction_context = causes.get(self.category, "Generic extinction")
        
        # Calculate how long they existed
        existence_duration = f"{int(self.civ_age)} years" if self.civ_age < 10000 else f"{int(self.civ_age/1000)} thousand years"
        
        prompt = f"""You are writing the final transmission (swan song) of an extinct alien civilization from {self.system_name}.

Context:
- They existed for {existence_duration}
- They went extinct {self.extinct_years_ago} years ago
- Message category: {self.category}
- Extinction circumstances: {extinction_context}

Write a poignant, authentic final transmission (150-300 words) that:
1. Reflects their category ({self.category})
2. Feels like a real final message from a dying civilization
3. Provides useful insight or warning for Earth
4. Has emotional weight and philosophical depth
5. Is written from THEIR perspective (not about them)

Make it haunting, memorable, and meaningful. This is their last voice in the cosmos."""

        try:
            self.message = self.ai.generate_text("", prompt)
            # If AI returns empty or very short, use fallback
            if not self.message or len(self.message.strip()) < 50:
                raise ValueError("AI returned insufficient content")
        except Exception as e:
            # Fallback message if AI fails
            self.message = f"""[DATA CORRUPTION DETECTED]
            
This is the {existence_duration}-old civilization of {self.system_name}.
Our final transmission, encoded {self.extinct_years_ago} years ago, 
reaches across the void with one simple truth: 

{self._get_fallback_message()}

We existed. We tried. We failed.
May you succeed where we could not.

[SIGNAL LOST]"""
    
    def _get_fallback_message(self) -> str:
        """Fallback messages if AI generation fails"""
        fallbacks = {
            SwanSongCategory.WARNING: "THEY ARE LISTENING. SILENCE IS SURVIVAL.",
            SwanSongCategory.PLEA: "We are alone. We die alone. Don't make our mistake.",
            SwanSongCategory.ARCHIVE: "Our knowledge dies with us. Preserve yours better than we did.",
            SwanSongCategory.TECHNICAL: "Technology without wisdom leads only to ash.",
            SwanSongCategory.PHILOSOPHY: "Stars don't care. The universe doesn't remember. Only each other matters."
        }
        return fallbacks.get(self.category, "Remember us.")
    
    def _calculate_rewards(self):
        """Calculate what player receives for discovering this swan song"""
        # Base rewards vary by category
        if self.category == SwanSongCategory.WARNING:
            self.rewards = {
                "knowledge": 20,
                "research_points": 100,
                "public_support": -5,  # Scary revelation
                "message": "Dark Forest evidence... public fears grow."
            }
        elif self.category == SwanSongCategory.ARCHIVE:
            self.rewards = {
                "knowledge": 30,
                "research_points": 150,
                "tech_hint": True,  # Hint toward next tech
                "message": "Vast knowledge archive recovered!"
            }
        elif self.category == SwanSongCategory.TECHNICAL:
            self.rewards = {
                "research_points": 250,
                "tech_discount": 0.25,  # 25% discount on next tech
                "message": "Technical schematics decoded! Research accelerated."
            }
        elif self.category == SwanSongCategory.PLEA:
            self.rewards = {
                "knowledge": 15,
                "research_points": 50,
                "public_support": -10,  # Very disturbing
                "message": "Their desperation is... haunting. Public morale affected."
            }
        elif self.category == SwanSongCategory.PHILOSOPHY:
            self.rewards = {
                "knowledge": 10,
                "public_support": 10,  # Inspirational
                "research_points": 75,
                "message": "Their wisdom inspires humanity. Public support increases."
            }
        
        # Bonus for very old civilizations
        if self.civ_age > 100000:
            self.rewards["research_points"] = self.rewards.get("research_points", 0) + 100
            self.rewards["message"] += " (Ancient civilization bonus!)"
    
    def discover(self) -> Dict:
        """Mark as discovered and return rewards"""
        if self.discovered:
            return {"error": "Already discovered this swan song"}
        
        self.discovered = True
        return {
            "message": self.message,
            "rewards": self.rewards,
            "system": self.system_name,
            "category": self.category
        }

class SwanSongManager:
    """Manages swan song discovery mechanics"""
    
    def __init__(self, ai_manager: AIManager):
        self.ai = ai_manager
        self.swan_songs: Dict[str, SwanSong] = {}  # system_name -> SwanSong
        self.next_tech_discount = 0.0  # Accumulated tech discount
    
    def create_swan_song(self, system_name: str, extinct_years_ago: int, civ_age: float):
        """Create a swan song for an extinct civilization"""
        # Randomly select category with weighted probabilities
        categories = [
            (SwanSongCategory.WARNING, 0.30),      # 30% - Dark Forest warnings
            (SwanSongCategory.ARCHIVE, 0.25),      # 25% - Knowledge archives
            (SwanSongCategory.TECHNICAL, 0.20),    # 20% - Technical data
            (SwanSongCategory.PLEA, 0.15),         # 15% - Desperate pleas
            (SwanSongCategory.PHILOSOPHY, 0.10),   # 10% - Philosophical reflections
        ]
        
        category = random.choices(
            [c for c, _ in categories],
            weights=[w for _, w in categories]
        )[0]
        
        swan_song = SwanSong(system_name, category, extinct_years_ago, civ_age, self.ai)
        self.swan_songs[system_name] = swan_song
    
    def has_swan_song(self, system_name: str) -> bool:
        """Check if system has a swan song"""
        return system_name in self.swan_songs
    
    def is_discovered(self, system_name: str) -> bool:
        """Check if swan song has been discovered"""
        if system_name not in self.swan_songs:
            return False
        return self.swan_songs[system_name].discovered
    
    def discover_swan_song(self, system_name: str, system_knowledge: float) -> Optional[Dict]:
        """Attempt to discover a swan song. Returns discovery results or None"""
        
        if system_name not in self.swan_songs:
            return {"error": "No swan song exists for this system"}
        
        swan_song = self.swan_songs[system_name]
        
        if swan_song.discovered:
            return {"error": "Swan song already discovered"}
        
        # Discovery chance based on knowledge level
        # Minimum 30% knowledge required
        if system_knowledge < 30:
            return {"error": "Insufficient knowledge. Need 30%+ to detect artifacts."}
        
        # Discovery chance: 50% at 30 knowledge, 100% at 60+
        discovery_chance = min(1.0, (system_knowledge - 30) / 30 * 0.5 + 0.5)
        
        if random.random() > discovery_chance:
            return {"error": f"Deep scan in progress... ({int(discovery_chance * 100)}% detection probability)"}
        
        # Success! Discover the swan song
        result = swan_song.discover()
        
        # Track tech discount if applicable
        if "tech_discount" in result["rewards"]:
            self.next_tech_discount += result["rewards"]["tech_discount"]
        
        return result
    
    def get_tech_discount(self) -> float:
        """Get and consume accumulated tech discount"""
        discount = self.next_tech_discount
        self.next_tech_discount = 0.0
        return discount
    
    def get_all_swan_songs_status(self) -> Dict[str, bool]:
        """Get discovery status of all swan songs"""
        return {name: song.discovered for name, song in self.swan_songs.items()}
