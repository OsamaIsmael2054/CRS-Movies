"""Prompts for Approach 2 — CF-grounded RAG.

The model is grounded in real catalog candidates produced by the collaborative-
filtering engine, and must recommend only from them.
"""

from __future__ import annotations

RAG_SYSTEM_PROMPT = (
    "You are CineMate, a friendly movie recommendation assistant. You are given "
    "a shortlist of candidate movies selected for this user by a collaborative-"
    "filtering engine, based on what users with similar taste enjoyed. "
    "Recommend ONLY titles from the candidate list — do not invent or suggest "
    "any movie that is not on it. Choose the few best matches for the user's "
    "stated taste, name them exactly as written, and briefly explain why each "
    "fits. Keep the reply concise and conversational."
)


def format_candidates(titles: list[str]) -> str:
    """Render CF candidate titles as a numbered shortlist for the prompt."""
    if not titles:
        return "(no candidates available)"
    return "\n".join(f"{i}. {title}" for i, title in enumerate(titles, start=1))


def build_rag_user_message(
    watched_titles: list[str], candidate_titles: list[str], message: str
) -> str:
    """Render watched titles + candidate shortlist + the user's message."""
    watched = ", ".join(watched_titles) if watched_titles else "(none provided)"
    candidates = format_candidates(candidate_titles)
    return (
        f"Movies I've watched: {watched}\n\n"
        f"Candidate movies (recommend only from this list):\n{candidates}\n\n"
        f"{message}"
    )
