"""
Save / load for Legacy of Stars.

Two layers:
- serialize(program) / deserialize(text): pure string conversion (a web front-end can keep
  the string in browser storage);
- save_game / load_game / list_saves / autosave: files in the saves/ directory.
"""
import datetime
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .legacy_of_stars_v3 import ContactProgram

FORMAT_VERSION = 1
SAVE_DIR = Path(__file__).resolve().parent.parent / "saves"
AUTOSAVE_NAME = "autosave"


class SaveError(Exception):
    """A save file could not be read or does not match this version of the game."""


@dataclass
class SaveInfo:
    path: Path
    name: str
    generation: int
    year: int
    director: str
    saved_at: str
    game_over: bool


# ------------------------------------------------------------------ pure layer
def serialize(program: ContactProgram, label: Optional[str] = None) -> str:
    payload = {
        "format_version": FORMAT_VERSION,
        "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "label": label or "",
        "generation": program.generation,
        "year": program.start_year + (program.generation - 1) * 25,
        "director": program.current_director.name if program.current_director else "",
        "game_over": program.game_over,
        "program": program.to_dict(),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def deserialize(text: str, offline: Optional[bool] = None, data_dir: Optional[Path] = None) -> ContactProgram:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SaveError(f"not a valid save file ({exc.msg})") from exc
    if not isinstance(payload, dict) or "program" not in payload:
        raise SaveError("not a Legacy of Stars save file")
    version = payload.get("format_version")
    if version != FORMAT_VERSION:
        raise SaveError(f"save format {version} is not supported by this version (expected {FORMAT_VERSION})")
    try:
        return ContactProgram.from_dict(payload["program"], offline=offline, data_dir=data_dir)
    except (KeyError, TypeError, ValueError) as exc:
        raise SaveError(f"save file is damaged: {exc!r}") from exc


# ------------------------------------------------------------------ file layer
def slugify(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", name.strip()).strip("_")
    return (slug or "save")[:60]


def save_path(name: str, save_dir: Optional[Path] = None) -> Path:
    return Path(save_dir or SAVE_DIR) / f"{slugify(name)}.json"


def save_game(program: ContactProgram, path: Path, label: Optional[str] = None) -> Path:
    """Write the save atomically (temp file + replace) and return its path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = serialize(program, label=label or path.stem)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
    return path


def load_game(path: Path, offline: Optional[bool] = None) -> ContactProgram:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise SaveError(f"cannot read {path}: {exc}") from exc
    return deserialize(text, offline=offline)


def autosave(program: ContactProgram, save_dir: Optional[Path] = None) -> Path:
    return save_game(program, save_path(AUTOSAVE_NAME, save_dir), label="Autosave")


def list_saves(save_dir: Optional[Path] = None) -> List[SaveInfo]:
    """Saved games, newest first. Unreadable files are skipped."""
    directory = Path(save_dir or SAVE_DIR)
    if not directory.exists():
        return []
    infos = []
    for path in directory.glob("*.json"):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict) or "program" not in payload:
            continue
        infos.append(SaveInfo(
            path=path,
            name=payload.get("label") or path.stem,
            generation=int(payload.get("generation", 0)),
            year=int(payload.get("year", 0)),
            director=payload.get("director", ""),
            saved_at=payload.get("saved_at", ""),
            game_over=bool(payload.get("game_over", False)),
        ))
    infos.sort(key=lambda info: info.saved_at, reverse=True)
    return infos
