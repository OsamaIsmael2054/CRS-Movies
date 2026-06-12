from dataclasses import dataclass

import asyncpg

from helpers.config import settings

# Sum positive-seed similarity minus disliked-seed similarity, drop seen items.
_RECOMMEND_SQL = """
WITH pos AS (SELECT DISTINCT unnest($1::text[]) AS item_id),
     neg AS (SELECT DISTINCT unnest($2::text[]) AS item_id),
     scored AS (
        SELECT s.item_b AS item_id, s.score AS score
        FROM item_similarity s JOIN pos ON s.item_a = pos.item_id
        UNION ALL
        SELECT s.item_b AS item_id, -$3::real * s.score AS score
        FROM item_similarity s JOIN neg ON s.item_a = neg.item_id
     )
SELECT scored.item_id, SUM(scored.score) AS score, i.title
FROM scored
JOIN items i ON i.item_id = scored.item_id
WHERE scored.item_id <> ALL($4::text[])
GROUP BY scored.item_id, i.title
HAVING SUM(scored.score) > 0
ORDER BY score DESC
LIMIT $5
"""

_POPULAR_SQL = """
SELECT p.item_id, p.n::real AS score, i.title
FROM item_popularity p
JOIN items i ON i.item_id = p.item_id
WHERE p.item_id <> ALL($1::text[])
ORDER BY p.n DESC
LIMIT $2
"""


_SIMILAR_SQL = """
SELECT s.item_b AS item_id, s.score AS score, i.title
FROM item_similarity s
JOIN items i ON i.item_id = s.item_b
WHERE s.item_a = $1 AND s.item_b <> $1
ORDER BY s.score DESC
LIMIT $2
"""

# User-based CF, computed at query time from the interaction matrix:
#  1. neighbors  = users who share the most movies with this watch history
#                  (overlap count as a crude user-user similarity), top-N.
#  2. candidates = movies those neighbors watched but this user hasn't,
#                  scored by summing the overlap of the neighbors who watched it.
# The seed history is excluded from the result, so the seed user never gets
# their own movies back (which also means they can't be their own neighbor).
_USER_CF_SQL = """
WITH seed AS (SELECT DISTINCT unnest($1::text[]) AS item_id),
     neighbors AS (
        SELECT x.user_id, COUNT(*) AS overlap
        FROM interactions x
        JOIN seed ON seed.item_id = x.item_id
        GROUP BY x.user_id
        ORDER BY overlap DESC
        LIMIT $2
     )
SELECT x.item_id, SUM(n.overlap)::real AS score, i.title
FROM interactions x
JOIN neighbors n ON n.user_id = x.user_id
JOIN items i ON i.item_id = x.item_id
WHERE x.item_id <> ALL($1::text[])
GROUP BY x.item_id, i.title
ORDER BY score DESC
LIMIT $3
"""


@dataclass
class Candidate:
    item_id: str
    title: str
    score: float


async def similar(
    conn: asyncpg.Connection, item_id: str, k: int | None = None
) -> list[Candidate]:
    """Return the top-``k`` catalog neighbors of ``item_id`` by CF similarity."""
    k = k or settings.cf_top_k
    rows = await conn.fetch(_SIMILAR_SQL, item_id, k)
    return [
        Candidate(item_id=r["item_id"], title=r["title"], score=float(r["score"]))
        for r in rows
    ]


async def recommend(
    conn: asyncpg.Connection,
    *,
    history_ids: list[str] | None = None,
    liked_ids: list[str] | None = None,
    disliked_ids: list[str] | None = None,
    k: int | None = None,
    dislike_penalty: float = 1.0,
) -> list[Candidate]:
    """Return up to ``k`` CF candidate movies the user hasn't seen.

    Positive seeds = history + likes; negative seeds = dislikes. Cold start
    (no positives) falls back to popularity, excluding seen items.
    """
    history_ids = history_ids or []
    liked_ids = liked_ids or []
    disliked_ids = disliked_ids or []
    k = k or settings.cf_top_k

    positives = list({*history_ids, *liked_ids})
    seen = list({*history_ids, *liked_ids, *disliked_ids})

    if not positives:
        rows = await conn.fetch(_POPULAR_SQL, seen, k)
    else:
        rows = await conn.fetch(
            _RECOMMEND_SQL, positives, disliked_ids, dislike_penalty, seen, k
        )

    return [
        Candidate(item_id=r["item_id"], title=r["title"], score=float(r["score"]))
        for r in rows
    ]


async def recommend_via_users(
    conn: asyncpg.Connection,
    *,
    history_ids: list[str],
    neighbors: int | None = None,
    k: int | None = None,
) -> list[Candidate]:
    """Recommend movies via user-based CF: what *similar users* watched.

    Finds the users whose watch history overlaps this one the most, then
    surfaces the movies those neighbors watched that aren't already in
    ``history_ids``, ranked by neighbor agreement. Returns ``[]`` when the
    history is empty (no one to be similar to).
    """
    history_ids = history_ids or []
    if not history_ids:
        return []
    neighbors = neighbors or settings.cf_user_neighbors
    k = k or settings.cf_top_k

    rows = await conn.fetch(_USER_CF_SQL, history_ids, neighbors, k)
    return [
        Candidate(item_id=r["item_id"], title=r["title"], score=float(r["score"]))
        for r in rows
    ]
