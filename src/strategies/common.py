"""Prompt helpers shared across more than one strategy."""

from __future__ import annotations


def build_user_message(watched_titles: list[str], message: str) -> str:
    """Render the user's watch history + their message into one prompt."""
    watched = ", ".join(watched_titles) if watched_titles else "(none provided)"
    return f"Movies I've watched: {watched}\n\n{message}"
