from collections import defaultdict, deque
from typing import Deque

# A single conversation turn as a role/content dict the LLM client understands.
Turn = dict[str, str]


class SessionStore:
    """In-memory conversation history keyed by ``session_id``.

    Each session keeps its most recent turns (user + assistant messages) so a
    strategy can feed prior context back to the LLM. History lives only in this
    process; restarting the server clears it. Swapping this for a Postgres-backed
    store later only requires keeping the same ``get`` / ``append`` interface.
    """

    def __init__(self, max_messages: int = 40) -> None:
        # ``maxlen`` bounds memory per session; oldest turns drop off first.
        self._max_messages = max_messages
        self._sessions: dict[str, Deque[Turn]] = defaultdict(
            lambda: deque(maxlen=max_messages)
        )

    def get(self, session_id: str | None) -> list[Turn]:
        """Prior turns for a session, oldest first. Empty for unknown sessions."""
        if not session_id:
            return []
        return list(self._sessions[session_id])

    def append(self, session_id: str | None, user: str, assistant: str) -> None:
        """Record one exchange (the user's message and the assistant's reply)."""
        if not session_id:
            return
        turns = self._sessions[session_id]
        turns.append({"role": "user", "content": user})
        turns.append({"role": "assistant", "content": assistant})

    def reset(self, session_id: str | None) -> None:
        """Forget a session's history (no-op if it doesn't exist)."""
        if session_id:
            self._sessions.pop(session_id, None)
