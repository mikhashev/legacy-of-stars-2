"""
Complete builder for legacy_of_stars_v3.py with Phase 1 + 1b
Applies all Dark Forest mechanics in one clean build
"""

# Read original file
with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

output = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # ===== CHANGE 1: Replace StarSystem class entirely =====
    if line.strip() == "class StarSystem:":
        output.append(line)
        i += 1
        
        # Skip old __init__ and methods, insert new implementation
        indent_count = 0
        while i < len(lines):
            if lines[i].strip().startswith("def __init__"):
                # Found __init__, skip until we hit next method
                while i < len(lines) and not (lines[i].strip().startswith("def ") and "__init__" not in lines[i]):
                    i += 1
                
                # Insert new __init__
                output.append("""    def __init__(self, name: str, distance: float):
        self.name = name
        self.distance = distance
        self.has_civilization = random.random() < 0.3
        
        if self.has_civilization:
            # === PHASE 1: Statistical Realism ===
            human_age = 100
            
            if random.random() < 0.75:
                civ_age = human_age * random.uniform(1.5, 50)
            else:
                civ_age = human_age * random.uniform(0.1, 0.9)
            
            if random.random() < 0.10:
                civ_age = human_age * random.uniform(10, 1000)
            
            self.civilization_age = civ_age
            self.civilization_stage = self._age_to_stage(civ_age)
            
            self.is_extinct = random.random() < 0.15
            if self.is_extinct:
                self.extinct_years_ago = random.randint(500, 5000)
                self.has_swan_song = random.random() < 0.8
                self.civilization_stage = None
            
            if not self.is_extinct:
                strategy_weights = {"L": 10, "LB": 30, "LR": 40, "LA": 15, "LBA": 5}
                self.true_strategy = random.choices(list(strategy_weights.keys()), weights=list(strategy_weights.values()))[0]
                
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
        self.pending_attack = None
    
    def _age_to_stage(self, age: float) -> CivilizationStage:
        if age < 50:
            return CivilizationStage.PRE_RADIO
        elif age < 200:
            return CivilizationStage.EARLY_RADIO
        elif age < 1000:
            return CivilizationStage.DIGITAL
        elif age < 10000:
            return CivilizationStage.INTERPLANETARY
        elif age < 100000:
            return CivilizationStage.INTERSTELLAR
        else:
            return CivilizationStage.POST_BIOLOGICAL
    
""")
                break
            elif lines[i].strip().startswith("class "):
                # Hit next class, break
                break
            i += 1
        continue
    
    # ===== CHANGE 2: Replace send_message entirely =====
    elif line.strip().startswith("def send_message(self"):
        # Skip old send_message
        while i < len(lines) and not (lines[i].strip().startswith("def ") and "send_message" not in lines[i]):
            i += 1
        
        # Insert new send_message
        output.append("""    def send_message(self, system_name: str, message_content: str):
        if self.action_points < 1:
            self.message = "Not enough Action Points!"
            return

        if system_name not in self.star_systems:
            self.message = f"System {system_name} not found in database."
            return
            
        system = self.star_systems[system_name]
        system.messages_sent.append((message_content, self.generation))
        logging.info(f"Message Sent to {system_name}: {message_content}")
        self.action_points -= 1
        
        # Extinct civilizations
        if system.has_civilization and system.is_extinct:
            self.message = f"Message sent to {system_name}. No response detected."
            return
        
        if not system.has_civilization or system.civilization_stage.value < CivilizationStage.EARLY_RADIO.value:
            self.message = f"Message sent to {system_name}, but no response capability detected."
            return
        
        round_trip_time = system.get_round_trip_time()
        
        # L Strategy
        if system.true_strategy == "L":
            self.message = f"Message sent to {system_name}. No response detected."
            logging.info(f"L Strategy: {system_name} - Silent")
            return
        
        # LA Strategy
        elif system.true_strategy == "LA":
            system.pending_attack = self.generation + round_trip_time
            self.message = f"Message sent to {system_name}. No response detected."
            logging.warning(f"LA Strategy: {system_name} - Attack in Gen {system.pending_attack}")
            return
        
        # LBA Strategy
        elif system.true_strategy == "LBA":
            if system.deception_level > 0.6:
                arrival_generation = self.generation + round_trip_time
                system.pending_attack = self.generation + round_trip_time + 2
                print(f"Generating response from {system_name}...")
                
                system_prompt = f"You are predatory aliens from {system_name} pretending to be friendly. Extract Earth's location and defenses. Be charming but subtly request tactical information."
                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                logging.warning(f"LBA Trap: {system_name}")
            else:
                system.pending_attack = self.generation + round_trip_time
                self.message = f"Message sent to {system_name}. No response detected."
            return
        
        # LR Strategy
        elif system.true_strategy == "LR":
            response_chance = 0.3 + (self.message_quality * 0.2) + (0.1 * system.civilization_stage.value)
            response_chance = min(0.85, response_chance)
            
            if random.random() < response_chance:
                arrival_generation = self.generation + round_trip_time
                print(f"Generating response from {system_name}...")
                
                system_prompt = f"You are cautious aliens from {system_name}. Reply defensively, ask about intent, avoid sharing coordinates."
                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Response expected in ~{round_trip_time * 25} years."
                self.public_support = min(100, self.public_support + 2)
            else:
                self.message = f"Message sent to {system_name}. No response (yet)."
            return
        
        # LB Strategy
        elif system.true_strategy == "LB":
            response_chance = 0.7 + (self.message_quality * 0.2)
            
            if random.random() < min(0.95, response_chance):
                arrival_generation = self.generation + round_trip_time
                print(f"Generating response from {system_name}...")
                
                system_prompt = f"You are enthusiastic aliens from {system_name}. Be optimistic, friendly, eager to share knowledge and culture."
                response_text = self.ai.generate_text(f"Human: {message_content}", system_prompt)
                system.pending_responses.append((response_text, arrival_generation))
                
                self.message = f"Message sent to {system_name}. Enthusiastic response expected!"
                self.public_support = min(100, self.public_support + 5)
            else:
                self.message = f"Message sent to {system_name}. Awaiting response..."
            return

""")
        continue
    
    # ===== CHANGE 3: Add attack processing to advance_generation =====
    elif "# Process pending messages" in line:
        output.append(line)
        i += 1
        
        # Copy the pending message processing
        while i < len(lines) and "# Passive Research Gain" not in lines[i]:
            output.append(lines[i])
            i += 1
        
        # Insert attack processing before passive research
        output.append("""        
        # === PHASE 1B: Process Attacks ===
        for system in self.star_systems.values():
            if system.pending_attack and system.pending_attack <= self.generation:
                logging.critical(f"ATTACK from {system.name}!")
                
                if system.civilization_stage.value >= self.tech_level + 2:
                    self.game_over = True
                    self.message = f"GAME OVER: Devastating attack from {system.name}. Earth annihilated."
                    return
                elif system.civilization_stage.value > self.tech_level:
                    self.public_support -= 40
                    self.funding -= 30
                    self.message = f"⚠️ ATTACK FROM {system.name.upper()}! Advanced weapons. Massive casualties."
                else:
                    self.public_support -= 25
                    self.funding -= 15
                    self.message = f"⚠️ ATTACK FROM {system.name.upper()}! Defended partially. Significant damage."
                
                system.pending_attack = None
                
                if self.funding < 20 or self.public_support < 10:
                    self.game_over = True
                    self.message += " Program shut down."
                    return
        
""")
        continue
    
    # Default: copy line as-is
    output.append(line)
    i += 1

# Write v3
with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.writelines(output)

print("✓ Created legacy_of_stars_v3.py with Phase 1 + 1b")
print("✓ Features: 75/25 age distribution, hidden strategies, Dark Forest responses, attack system")
