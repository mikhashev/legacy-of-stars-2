"""
Fix bugs in legacy_of_stars_v3.py:
1. describe_civilization() doesn't handle extinct civilizations (stage=None)  
2. Logging uses single game.log file instead of timestamped sessionlogs
"""

with open(r"c:\Users\mike\Documents\Antigravity Test\Legacy-of-stars\legacy_of_stars_v3.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix 1: Replace describe_civilization method to handle extinct civilizations
old_describe = '''    def describe_civilization(self) -> str:
        """Get description of civilization based on current knowledge"""
        if not self.has_civilization:
            return "No signs of civilization detected."
            
        if self.knowledge < 20:
            return "Possible artificial signals detected."
        elif self.knowledge < 40:
            return f"Civilization detected at {self.civilization_stage.name} stage."'''

new_describe = '''    def describe_civilization(self) -> str:
        """Get description of civilization based on current knowledge"""
        if not self.has_civilization:
            return "No signs of civilization detected."
        
        # Handle extinct civilizations (civilization_stage is None)
        if self.is_extinct:
            if self.knowledge < 20:
                return "Faint signals detected. System appears lifeless."
            elif self.knowledge < 60:
                return f"EXTINCT CIVILIZATION detected. Dead for ~{self.extinct_years_ago} years."
            else:
                swan_info = " Data archives may exist." if self.has_swan_song else " No archives detected."
                return f"EXTINCT: Civilization collapsed {self.extinct_years_ago} years ago.{swan_info}"
            
        if self.knowledge < 20:
            return "Possible artificial signals detected."
        elif self.knowledge < 40:
            return f"Civilization detected at {self.civilization_stage.name} stage."'''

content = content.replace(old_describe, new_describe)

# Fix 2: Replace logging setup with timestamped files
old_logging = '''if __name__ == "__main__":
    logging.basicConfig(filename='game.log', level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    logging.info("Game started.")
    game = GameInterface()
    game.play()'''

new_logging = '''if __name__ == "__main__":
    # Create timestamped log file for this session
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"game_{timestamp}.log"
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("="*50)
    logging.info(f"LEGACY OF STARS - Session Started")
    logging.info(f"Log file: {log_filename}")
    logging.info("="*50)
    
    print(f"\\nLogging to: {log_filename}\\n")
    
    game = GameInterface()
    game.play()'''

content = content.replace(old_logging, new_logging)

# Write fixed file
with open(r"c:\Users\mike\Documents\Antigravity Test\legacy-of-stars\legacy_of_stars_v3.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✅ Fixed bugs in legacy_of_stars_v3.py:")
print("  1. describe_civilization() now handles extinct civilizations")
print("  2. Logging now creates timestamped files (game_YYYYMMDD_HHMMSS.log)")
