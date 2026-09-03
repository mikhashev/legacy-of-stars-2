"""
Documentation link checker (stdlib only).

Walks `README.md`, `web/README.md` and every `docs/**/*.md`, extracts:
  - Markdown links: `[text](path)`
  - bare `docs/...` path mentions (e.g. inside backticks or plain prose)

and checks that each local target exists on disk. Markdown links are resolved
relative to the directory of the file that contains them; bare `docs/...`
mentions are resolved relative to the repository root, since that is how they
are written throughout the repo regardless of which file mentions them.

Ignored (not checked, not counted as missing):
  - http(s):// and mailto: links
  - anchor-only links (`#section`)
  - `file:///...` links inside `docs/history/**` (pre-existing local-machine
    paths from an old contributor setup); these are counted separately as
    "legacy external" in the summary.

Exit code: 1 if any local target is missing, 0 otherwise.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
BARE_DOCS_RE = re.compile(r"(?<![\w/])docs/[A-Za-z0-9_\-./]+\.[A-Za-z0-9]+")


def target_files() -> list[pathlib.Path]:
    files = [ROOT / "README.md", ROOT / "web" / "README.md"]
    files += sorted((ROOT / "docs").rglob("*.md"))
    return [f for f in files if f.exists()]


def is_ignored_link(link: str) -> bool:
    link = link.strip()
    if not link:
        return True
    if link.startswith(("http://", "https://", "mailto:")):
        return True
    if link.startswith("#"):
        return True
    if link.startswith("@"):
        # A social-handle-style mention used as a link target (e.g.
        # `[@SETIInstitute](@SETIInstitute)`), not a repository path.
        return True
    return False


def strip_anchor_and_title(link: str) -> str:
    # Drop an optional Markdown title: (path "title")
    link = link.split(' "', 1)[0].strip()
    # Drop a URL fragment: path#anchor
    link = link.split("#", 1)[0]
    return link.strip()


def check_file(path: pathlib.Path):
    """Return (missing, legacy_external, checked_count) for one file."""
    text = path.read_text(encoding="utf-8")
    missing = []
    legacy_external = 0
    checked = 0
    is_history = (ROOT / "docs" / "history") in path.parents

    seen_spans = []

    for m in MD_LINK_RE.finditer(text):
        raw = m.group(1)
        seen_spans.append(m.span(1))
        if raw.strip().startswith("file:///"):
            if is_history:
                legacy_external += 1
                continue
            # A file:// link outside docs/history is not something this repo
            # uses on purpose; still skip it (not a repo-relative target).
            legacy_external += 1
            continue
        if is_ignored_link(raw):
            continue
        link = strip_anchor_and_title(raw)
        if not link:
            continue
        checked += 1
        target = (path.parent / link).resolve()
        if not target.exists():
            missing.append((path, raw, target))

    for m in BARE_DOCS_RE.finditer(text):
        span = m.span()
        # Skip anything already captured as the destination of a Markdown link,
        # so we do not double-report the same reference.
        if any(s[0] <= span[0] and span[1] <= s[1] for s in seen_spans):
            continue
        raw = m.group(0)
        checked += 1
        target = (ROOT / raw).resolve()
        if not target.exists():
            missing.append((path, raw, target))

    return missing, legacy_external, checked


def main() -> int:
    all_missing = []
    total_checked = 0
    total_legacy = 0

    for path in target_files():
        missing, legacy_external, checked = check_file(path)
        all_missing.extend(missing)
        total_checked += checked
        total_legacy += legacy_external

    rel = lambda p: p.relative_to(ROOT).as_posix()

    print(f"Checked {total_checked} local reference(s) across {len(target_files())} file(s).")
    print(f"Legacy external (file:/// in docs/history): {total_legacy}")

    if all_missing:
        print(f"\nMissing targets ({len(all_missing)}):")
        for src, raw, target in all_missing:
            print(f"  {rel(src)}: '{raw}' -> {target} (not found)")
        return 1

    print("No missing targets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
