import asyncpg
from rapidfuzz import fuzz, process

from src.stores.cf import Candidate


async def search_titles(
    conn: asyncpg.Connection, query: str, limit: int = 8
) -> list[Candidate]:
    """Fuzzy-match ``query`` against catalog titles, best first.

    ``score`` is the rapidfuzz similarity (0-100), not a CF score.
    """
    query = (query or "").strip()
    if not query:
        return []

    rows = await conn.fetch("SELECT item_id, title FROM items")
    titles = {r["item_id"]: r["title"] for r in rows}

    matches = process.extract(
        query, titles, scorer=fuzz.WRatio, limit=limit, score_cutoff=60
    )
    # process.extract over a mapping yields (title, score, item_id) tuples.
    return [
        Candidate(item_id=item_id, title=title, score=float(score))
        for title, score, item_id in matches
    ]
