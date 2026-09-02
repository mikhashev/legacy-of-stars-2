"""
Legacy of Stars - Launcher
Run from anywhere:  python run_game.py
"""
import datetime
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)  # data/, logs/ and saves/ are resolved relative to the project root
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.console import QuitGame, configure_console  # noqa: E402

configure_console()


def setup_logging() -> str:
    """Create logs/game_<timestamp>.log (UTF-8) and return its path."""
    os.makedirs("logs", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"logs/game_{timestamp}.log"
    logging.basicConfig(
        filename=log_filename,
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        encoding="utf-8",
    )
    logging.info("=" * 50)
    logging.info("LEGACY OF STARS - Session Started")
    logging.info(f"Log file: {log_filename}")
    logging.info("=" * 50)
    return log_filename


def main() -> int:
    log_filename = setup_logging()
    print("\nLegacy of Stars")
    print(f"Logging to: {log_filename}\n")

    try:
        from src.game_interface import start_menu

        game = start_menu()
        if game is None:
            print("Goodbye.")
            return 0
        game.run_opening_scenario()  # skipped automatically for loaded games
        game.play()
    except QuitGame:
        print("\nGame closed.")
        return 0
    except Exception as exc:  # noqa: BLE001 - last-resort handler for the player
        logging.critical("CRITICAL ERROR", exc_info=True)
        print(f"\nCRITICAL ERROR: {exc}")
        print(f"Details were written to {log_filename}")
        if sys.stdin is not None and sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
