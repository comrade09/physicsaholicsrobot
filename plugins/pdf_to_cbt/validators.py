"""
Lightweight, no-extra-API-call validation for the HTML that Gemini returns.

These are cheap sanity checks -- not a full HTML parser -- meant to catch
obviously broken or truncated output before we send it to the user, so we
can retry the Gemini call once instead of shipping a broken file.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

MAX_TELEGRAM_DOCUMENT_BYTES = 50 * 1024 * 1024  # Telegram bot API document limit


def validate_cbt_html(html: str) -> tuple[bool, Optional[str]]:
    """
    Validate that `html` looks like a complete, working CBT test file.

    Returns:
        (True, None) if the HTML passes all checks.
        (False, reason) if it fails, where `reason` is a short human-readable
        explanation -- used both for logging and for building the Gemini
        retry prompt.
    """
    if not html or not html.strip():
        return False, "Gemini returned empty output."

    stripped = html.strip().lower()
    if not (stripped.startswith("<!doctype html") or stripped.startswith("<html")):
        return False, "Output does not start with <!DOCTYPE html> or <html>."

    lowered = html.lower()
    if "<script" not in lowered:
        return False, "Output is missing the embedded <script> block with question data."

    # Heuristic check that question data actually made it into the script
    # block, not just an empty/placeholder <script></script>.
    if "stem_html" not in lowered and "question" not in lowered:
        return False, "Output's script block does not appear to contain question data."

    if "</html>" not in lowered:
        return False, "Output appears truncated (no closing </html> tag)."

    size_bytes = len(html.encode("utf-8"))
    if size_bytes > MAX_TELEGRAM_DOCUMENT_BYTES:
        size_mb = size_bytes / (1024 * 1024)
        return False, (
            f"Generated HTML is {size_mb:.1f}MB, which exceeds Telegram's 50MB "
            f"document limit. Embedded images likely need to be recompressed "
            f"or downscaled."
        )

    return True, None
