import asyncpg
from langchain_core.tools import tool

from src.stores.catalog import search_titles
from src.stores.cf import Candidate, recommend, recommend_via_users, similar


def _format(candidates: list[Candidate]) -> str:
    """Render candidates as a numbered, id-tagged shortlist for the model."""
    if not candidates:
        return "No results."
    return "\n".join(
        f"{i}. {c.title} (id={c.item_id}, score={round(c.score, 3)})"
        for i, c in enumerate(candidates, start=1)
    )


def create_recommend_tool(pool: asyncpg.Pool, history: list[str]):
    """Build the CF candidate tool bound to this request's pool and history."""

    @tool
    async def recommend_candidates(
        seed_item_ids: list[str] | None = None, k: int = 10
    ) -> str:
        """Get collaborative-filtering movie candidates for this user.

        Call with no arguments to use the user's watch history, or pass
        seed_item_ids (catalog ids) to seed from specific movies. Returns a
        newline-separated shortlist of real catalog titles to recommend from.
        """
        seeds = seed_item_ids or history
        async with pool.acquire() as conn:
            candidates = await recommend(conn, history_ids=seeds, k=k)
        return _format(candidates)

    return recommend_candidates


def create_similar_users_tool(pool: asyncpg.Pool, history: list[str]):
    """Build the user-based CF tool: recommend what *similar users* watched."""

    @tool
    async def recommend_from_similar_users(
        seed_item_ids: list[str] | None = None, k: int = 10
    ) -> str:
        """Recommend movies based on users with a similar taste to this user.

        Finds the users whose watch history overlaps this user's the most, then
        returns the movies those neighbors watched that this user hasn't seen,
        ranked by how many neighbors agree. Call with no arguments to use the
        user's full watch history, or pass seed_item_ids (e.g. their 3 most
        recently watched movies) to define taste from just those. Use this when
        the user hasn't named any movies they like, as a complement to
        recommend_candidates. Returns a newline-separated shortlist of real
        catalog titles.
        """
        seeds = seed_item_ids or history
        async with pool.acquire() as conn:
            candidates = await recommend_via_users(conn, history_ids=seeds, k=k)
        return _format(candidates)

    return recommend_from_similar_users


def create_search_tool(pool: asyncpg.Pool):
    """Build the title-search tool (resolves a mentioned title to a catalog id)."""

    @tool
    async def search_movies(query: str, limit: int = 8) -> str:
        """Find catalog movies whose title matches a query, best match first.

        Use this to resolve a movie the user mentions by name into a catalog id,
        then pass that id as a seed to recommend_candidates or similar_movies.
        Tolerates misspellings and partial titles.
        """
        async with pool.acquire() as conn:
            matches = await search_titles(conn, query, limit=limit)
        return _format(matches)

    return search_movies


def create_similar_tool(pool: asyncpg.Pool):
    """Build the 'more like this one movie' tool over CF item neighbors."""

    @tool
    async def similar_movies(item_id: str, k: int = 10) -> str:
        """Get catalog movies most similar to one specific movie (by catalog id).

        Use this for 'movies like X' once you have X's id from search_movies.
        Returns a newline-separated shortlist of real catalog titles.
        """
        async with pool.acquire() as conn:
            neighbors = await similar(conn, item_id, k=k)
        return _format(neighbors)

    return similar_movies
