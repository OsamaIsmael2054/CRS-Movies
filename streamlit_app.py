"""Streamlit test UI for the Movies-CRS API.

Run the API first (``uvicorn src.main:app --port 8000``), then:

    streamlit run streamlit_app.py

It POSTs to ``/chat`` and streams the reply token-by-token. The request carries
only ``user_id`` (plus the message and mode); the server looks that user's watch
history up itself. The optional history preview in the sidebar reads Postgres
directly, purely so you can see what the server will use.
"""

from __future__ import annotations

import asyncio

import requests
import streamlit as st

# Optional: direct DB access just to preview a user's history in the sidebar.
try:
    from src.stores.database import connect

    _DB_AVAILABLE = True
except Exception:  # pragma: no cover - app still works API-only
    _DB_AVAILABLE = False

DEFAULT_API = "http://localhost:8000"
DEFAULT_USER = "A30Q8X8B1S3GGT"
MODES = ["fewshot", "rag", "agent"]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def db_user_history(user_id: str) -> list[tuple[str, str]] | None:
    """The movies this user watched (id, title). None if the DB is unreachable."""
    if not user_id:
        return []

    async def _run() -> list[tuple[str, str]]:
        conn = await connect()
        try:
            rows = await conn.fetch(
                "SELECT i.item_id, it.title FROM interactions i "
                "JOIN items it ON it.item_id = i.item_id "
                "WHERE i.user_id = $1 ORDER BY it.title",
                user_id,
            )
            return [(r["item_id"], r["title"]) for r in rows]
        finally:
            await conn.close()

    try:
        return asyncio.run(_run())
    except Exception:  # noqa: BLE001 - DB preview is optional
        return None


def check_health(api: str) -> tuple[bool, str]:
    try:
        r = requests.get(f"{api}/health", timeout=5)
        r.raise_for_status()
        return True, r.json().get("status", "ok")
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def stream_chat(api: str, payload: dict):
    """Yield decoded text chunks from the streaming /chat endpoint."""
    with requests.post(f"{api}/chat", json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        for chunk in r.iter_content(chunk_size=None):
            if chunk:
                yield chunk.decode("utf-8", errors="ignore")


# --------------------------------------------------------------------------- #
# State
# --------------------------------------------------------------------------- #
st.set_page_config(page_title="Movies-CRS Tester", page_icon="🎬", layout="wide")

if "messages" not in st.session_state:
    st.session_state.messages = []


# --------------------------------------------------------------------------- #
# Sidebar — connection, mode, user
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ Settings")
    api = st.text_input("API base URL", value=DEFAULT_API).rstrip("/")

    if st.button("Check API health", use_container_width=True):
        ok, msg = check_health(api)
        (st.success if ok else st.error)(
            f"API: {msg}" if ok else f"Unreachable: {msg}"
        )

    mode = st.radio("Strategy (mode)", MODES, index=1)
    user_id = st.text_input("user_id", value=DEFAULT_USER)

    if _DB_AVAILABLE:
        with st.expander("👁️ Preview this user's history"):
            history = db_user_history(user_id) if user_id else []
            if history is None:
                st.warning("DB unreachable — can't preview (API still works).")
            elif not history:
                st.caption("No history for this user (cold start → popularity).")
            else:
                st.caption(f"{len(history)} movies the server will use:")
                for item_id, title in history:
                    st.write(f"{title}  \n`{item_id}`")


# --------------------------------------------------------------------------- #
# Main — chat
# --------------------------------------------------------------------------- #
st.title("🎬 Movies-CRS Tester")
st.caption(
    f"Mode **{mode}** · user `{user_id or '(none)'}` · the server looks up this "
    "user's history; each message is a single turn."
)

if st.button("🔄 Reset conversation"):
    st.session_state.messages = []
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask for a recommendation…"):
    if not user_id:
        st.error("Set a user_id in the sidebar first.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {"message": prompt, "user_id": user_id, "mode": mode}
    with st.chat_message("assistant"):
        try:
            reply = st.write_stream(stream_chat(api, payload))
        except Exception as exc:  # noqa: BLE001
            reply = f"⚠️ Request failed: {exc}"
            st.error(reply)
    st.session_state.messages.append({"role": "assistant", "content": reply})
