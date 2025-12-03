"""
Script to automatically apply Phase 1 + 1b changes to create legacy_of_stars_v3.py
This creates a clean implementation from the original file
"""

import re

# Read the original file
with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars.py", "r", encoding="utf-8") as f:
    content = f.read()

# ===== CHANGE 1: Replace StarSystem.__init__ =====
old_init = r'''class StarSystem:
    def __init__\(self, name: str, distance: float\):
        self\.name = name
        self\.distance = distance  # In light years
        self\.has_civilization = random\.random\(\) < 0\.3
        
        if self\.has_civilization:
            # Most civilizations are at lower technological levels
            weights = \[20, 30, 25, 15, 7, 3\]
            stage_values = list\(range\(len\(CivilizationStage\)\)\)
            self\.civilization_stage = CivilizationStage\(random\.choices\(stage_values, weights=weights\)\[0\]\)
            self\.civilization_attitude = random\.uniform\(0\.2, 0\.8\)  # 0 = hostile, 1 = friendly
        else:
            self\.civilization_stage = None
            self\.civilization_attitude = 0
            
        self\.knowledge = 0  # How much we know about this system
        self\.messages_sent = \[\]  # List of messages sent to this system
        self\.pending_responses = \[\]  # Messages en route back to Earth
        self\.received_messages = \[\]  # Messages we've received and analyzed'''

new_init = '''class StarSystem:
    def __init__(self, name: str, distance: float):
        self.name = name
        self.distance = distance  # In light years
        self.has_civilization = random.random() < 0.3
        
        if self.has_civilization:
            # === PHASE 1: Statistical Realism (75/25 Rule) ===
            human_age = 100  # Years since radio technology
            
            # 75% older, 25% younger
            if random.random() < 0.75:
                civ_age = human_age * random.uniform(1.5, 50)
            else:
                civ_age = human_age * random.uniform(0.1, 0.9)
            
            # 10% ancient
            if random.random() < 0.10:
                civ_age = human_age * random.uniform(10, 1000)
            
            self.civilization_age = civ_age
            self.civilization_stage = self._age_to_stage(civ_age)
            
            # 15% extinct
            self.is_extinct = random.random() < 0.15
            if self.is_extinct:
                self.extinct_years_ago = random.randint(500, 5000)
                self.has_swan_song = random.random() < 0.8
                self.civilization_stage = None
            
            # Hidden strategies
            if not self.is_extinct:
                strategy_weights = {"L": 10, "LB": 30, "LR": 40, "LA": 15, "LBA": 5}
                strategies = list(strategy_weights.keys())
                weights = list(strategy_weights.values())
                self.true_strategy = random.choices(strategies, weights=weights)[0]
                
                if self.civilization_age > human_age * 2:
                    self.deception_level = random.uniform(0.3, 1.0)
                else:
                    self.deception_level = random.uniform(0, 0.5)
            else:
               self.true_strategy = None
                self.deception_level = 0
            
            self.civilization_attitude = random.uniform(0.2, 0.8)
        else:
            self.civilization_age = 0
            self.civilization_stage = None
            self.civilization_attitude = 0
            self.is_extinct = False
            self.has_swan_song = False
            self.true_strategy = None
            self.deception_level = 0
            
        self.knowledge = 0
        self.messages_sent = []
        self.pending_responses = []
        self.received_messages = []
        self.pending_attack = None'''

content = re.sub(old_init, new_init, content, flags=re.DOTALL)

print("Applied StarSystem.__init__ changes")

# Write to v3
with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Created legacy_of_stars_v3.py")
print("✓ Step 1/3 complete")
