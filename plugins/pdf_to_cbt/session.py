"""
In-memory session manager for the pdf_to_cbt plugin.

Tracks, per Telegram user, which conversion mode they picked and which
PDF file(s) they've uploaded so far. This is intentionally simple and
resets on bot restart -- swap this module-level dict for SQLite/Redis
later without touching handler.py if you need persistence across restarts.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MODE_SINGLE = "single"
MODE_DOUBLE = "double"

STATUS_AWAITING_MODE = "awaiting_mode"
STATUS_AWAITING_FILES = "awaiting_files"
STATUS_PROCESSING = "processing"

# user_id -> {"mode": str | None, "files": list[str], "status": str}
_sessions: dict[int, dict] = {}


def start_session(user_id: int) -> None:
    """Begin a new /pdf2cbt session for this user, clearing any old one."""
    _sessions[user_id] = {"mode": None, "files": [], "status": STATUS_AWAITING_MODE}
    logger.info("Started pdf_to_cbt session for user %s", user_id)


def has_session(user_id: int) -> bool:
    """Return True if this user currently has an active session."""
    return user_id in _sessions


def set_mode(user_id: int, mode: str) -> None:
    """Record the chosen conversion mode and move to file-collection state."""
    if user_id not in _sessions:
        start_session(user_id)
    _sessions[user_id]["mode"] = mode
    _sessions[user_id]["status"] = STATUS_AWAITING_FILES


def get_mode(user_id: int) -> Optional[str]:
    session_data = _sessions.get(user_id)
    return session_data["mode"] if session_data else None


def add_file(user_id: int, filepath: str) -> None:
    """Attach a downloaded PDF path to this user's session."""
    if user_id not in _sessions:
        start_session(user_id)
    _sessions[user_id]["files"].append(filepath)


def get_files(user_id: int) -> list[str]:
    session_data = _sessions.get(user_id)
    return session_data["files"] if session_data else []


def files_needed(user_id: int) -> int:
    """How many more PDF files this user still needs to upload."""
    session_data = _sessions.get(user_id)
    if not session_data or not session_data["mode"]:
        return 0
    required = 1 if session_data["mode"] == MODE_SINGLE else 2
    return max(0, required - len(session_data["files"]))


def is_ready(user_id: int) -> bool:
    """True once the user has uploaded all files required by their chosen mode."""
    return has_session(user_id) and get_mode(user_id) is not None and files_needed(user_id) == 0


def set_status(user_id: int, status: str) -> None:
    if user_id in _sessions:
        _sessions[user_id]["status"] = status


def get_status(user_id: int) -> Optional[str]:
    session_data = _sessions.get(user_id)
    return session_data["status"] if session_data else None


def clear_session(user_id: int) -> None:
    """Remove this user's session entirely (used by /cancelpdf and after completion)."""
    _sessions.pop(user_id, None)
    logger.info("Cleared pdf_to_cbt session for user %s", user_id)
