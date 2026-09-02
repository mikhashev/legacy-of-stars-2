"""
Console helpers for Legacy of Stars.

Keeps the terminal layer safe on every platform:
- UTF-8 output even when stdout is redirected (Windows cp1252 pipes would
  otherwise raise UnicodeEncodeError on the game's emoji).
- EOF / Ctrl+C on any prompt becomes a single QuitGame exception that the
  launcher turns into a clean exit instead of a traceback.

The game engine itself never touches the console; only the UI layer
(game_interface.py, run_game.py) imports this module.
"""
import sys


class QuitGame(Exception):
    """Raised when the player closes the game (EOF on stdin or Ctrl+C)."""


def configure_console() -> None:
    """Force UTF-8 on stdout/stderr when the current encoding is not UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        encoding = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if encoding != "utf8":
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def read_input(prompt: str = "") -> str:
    """input() that converts EOF and Ctrl+C into QuitGame and strips whitespace."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        raise QuitGame()
