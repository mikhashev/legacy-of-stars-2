"""
Legacy of Stars - Launcher
Use this script to run the game from the project root.
"""
import sys
import os
from pathlib import Path

# Ensure we're running from the project root
root_path = Path(__file__).parent
os.chdir(root_path)  # Set working directory to root
sys.path.insert(0, str(root_path))

# Import the game
try:
    from src.legacy_of_stars_v3 import GameInterface, logging, datetime
except ImportError as e:
    print(f"Error importing game modules: {e}")
    print("Please ensure you are running this script with: python run_game.py")
    input("\nPress Enter to exit...")
    sys.exit(1)

if __name__ == "__main__":
    # Create timestamped log file in logs directory
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/game_{timestamp}.log"
    
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logging.info("="*50)
    logging.info(f"LEGACY OF STARS - Session Started")
    logging.info(f"Log file: {log_filename}")
    logging.info("="*50)
    
    print(f"\nLegacy of Stars")
    print(f"Logging to: {log_filename}\n")
    
    try:
        game = GameInterface()
        # Present WOW! Signal opening scenario if applicable
        if hasattr(game.program, 'wow_signal'):
             game.program.wow_signal.present_opening_scenario()
        
        game.play()
    except Exception as e:
        print(f"\nCRITICAL ERROR: {e}")
        logging.critical(f"CRITICAL ERROR: {e}", exc_info=True)
        import traceback
        traceback.print_exc()
        input("\nPress Enter to exit...")
