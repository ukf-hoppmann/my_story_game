from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path

from harness_config import ROOT_PROJECT


def state_dir() -> Path:
    data_dir = os.environ.get("CLAUDE_PLUGIN_DATA")
    if data_dir:
        return Path(data_dir)
    return Path(tempfile.gettempdir()) / "claude-harness"


def _safe(session_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", session_id)


def dirty_marker(session_id: str) -> Path:
    """JSON list of the projects whose backlog changed; an empty file means the root project."""
    return state_dir() / f"backlog-dirty-{_safe(session_id)}"


def read_names(path: Path) -> set[str]:
    try:
        text = path.read_text()
    except OSError:
        return set()
    if not text.strip():
        return {ROOT_PROJECT}
    try:
        return {str(name) for name in json.loads(text)}
    except (ValueError, TypeError):
        return {ROOT_PROJECT}


def write_names(path: Path, names: set[str]) -> None:
    """Store names; an empty set removes the file."""
    if not names:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(names)))


def notes_changed_file(session_id: str) -> Path:
    """JSON list of "<project>\t<path relative to the project>" for notes files changed in the session."""
    return state_dir() / f"backlog-notes-{_safe(session_id)}.json"


def read_changed_notes(session_id: str) -> set[tuple[str, str]]:
    """(project, path relative to the project) of the notes files changed in the session."""
    try:
        entries = json.loads(notes_changed_file(session_id).read_text())
    except (OSError, ValueError):
        return set()
    return {tuple(str(entry).split("\t", 1)) for entry in entries if "\t" in str(entry)}


def write_changed_notes(session_id: str, notes: set[tuple[str, str]]) -> None:
    """Store the changed notes files; an empty set removes the file."""
    path = notes_changed_file(session_id)
    if not notes:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(f"{project}\t{relative}" for project, relative in notes)))


def items_file(session_id: str, kind: str) -> Path:
    """JSON list of "<project>\\t<ID>": backlog items whose `notes` were changed or which are `active` in the session."""
    return state_dir() / f"backlog-items-{kind}-{_safe(session_id)}.json"


def read_items(session_id: str, kind: str) -> set[tuple[str, str]]:
    try:
        entries = json.loads(items_file(session_id, kind).read_text())
    except (OSError, ValueError):
        return set()
    return {tuple(str(entry).split("\t", 1)) for entry in entries if "\t" in str(entry)}


def add_item(session_id: str, kind: str, project: str, identifier: str) -> None:
    items = read_items(session_id, kind) | {(project, identifier)}
    path = items_file(session_id, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(f"{p}\t{i}" for p, i in items)))


def delivered_notices_file(session_id: str) -> Path:
    return state_dir() / f"backlog-notices-{_safe(session_id)}.json"


def daily_reminded_file(session_id: str) -> Path:
    return state_dir() / f"daily-reminded-{_safe(session_id)}.json"


def techdocs_marker(session_id: str, kind: str, project: str = ROOT_PROJECT) -> Path:
    """kind: 'project' (project files changed), 'docs' (docs changed), 'reminded'; per project."""
    if project == ROOT_PROJECT:
        return state_dir() / f"techdocs-{kind}-{_safe(session_id)}"
    return state_dir() / f"techdocs-{kind}-{_safe(project)}--{_safe(session_id)}"


def architecture_read_file(session_id: str) -> Path:
    return state_dir() / f"architecture-read-{_safe(session_id)}.json"


def semver_reported_file(session_id: str) -> Path:
    return state_dir() / f"semver-reported-{_safe(session_id)}.json"
