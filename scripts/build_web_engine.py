"""
Build `web/public/engine.zip`: the Python engine as Pyodide unpacks it (docs/plans/web_version_plan.md, W1).

The archive holds exactly what `src/web_api.py` needs at run time:

    src/*.py      the engine package (with __init__.py, so `from src.web_api import ...` works)
    data/**/*.json   star catalog, tech tree, templates/, llm_providers.json

Left out: __pycache__, tests, legacy, saves, logs, media, docs and every non-JSON file.
The worker unpacks the archive into /engine and puts that directory on sys.path, so the
layout inside the zip is the repository layout rooted at the repository directory itself.

Usage:  python scripts/build_web_engine.py [--out PATH]
"""
from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "web" / "public" / "engine.zip"
EXCLUDED_DIRS = {"__pycache__", "templates_disabled"}


def collect() -> list[tuple[Path, str]]:
    """(absolute path, name inside the archive) for every file that goes in."""
    files: list[tuple[Path, str]] = []

    for path in sorted((ROOT / "src").glob("*.py")):
        files.append((path, f"src/{path.name}"))

    for path in sorted((ROOT / "data").rglob("*.json")):
        if any(part in EXCLUDED_DIRS for part in path.relative_to(ROOT).parts):
            continue
        files.append((path, path.relative_to(ROOT).as_posix()))

    return files


def build(out: Path) -> Path:
    files = collect()
    names = {name for _, name in files}
    if "src/__init__.py" not in names:
        raise SystemExit("src/__init__.py is missing: the engine would not be importable in Pyodide")
    if "src/web_api.py" not in names:
        raise SystemExit("src/web_api.py is missing: the browser has no entry point")

    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, name in files:
            archive.write(path, name)

    size = out.stat().st_size
    print(f"{out.relative_to(ROOT).as_posix()}: {len(files)} files, {size:,} bytes ({size / 1024:.1f} KiB)")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output path (default: web/public/engine.zip)")
    build(parser.parse_args().out)


if __name__ == "__main__":
    main()
