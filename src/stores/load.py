import asyncio

import asyncpg

from helpers.config import settings
from helpers.io_utils import iter_jsonl, read_json


async def _apply_schema(conn: asyncpg.Connection) -> None:
    schema_sql = settings.schema_path.read_text(encoding="utf-8")
    await conn.execute(schema_sql)


def _collect_rows() -> dict:
    """Read the source files and build de-duplicated row collections."""
    data = settings.data_dir

    # Base catalogs.
    items: dict[str, str] = dict(read_json(data / "item_map.json"))
    users: dict[str, int] = dict(read_json(data / "user_ids.json"))

    interactions: set[tuple[str, str]] = set()  # (user_id, item_id)
    might_like: set[tuple[str, str]] = set()  # (user_id, item_id)

    next_idx = (max(users.values()) + 1) if users else 0

    def ensure_item(item_id: str) -> None:
        if item_id not in items:
            items[item_id] = item_id  # fallback title = id (data is slightly dirty)

    def ensure_user(user_id: str) -> None:
        nonlocal next_idx
        if user_id not in users:
            users[user_id] = next_idx
            next_idx += 1

    for record in iter_jsonl(data / "final_data.jsonl"):
        user_id, info = next(iter(record.items()))
        ensure_user(user_id)

        for item_id in info.get("history_interaction", []):
            ensure_item(item_id)
            interactions.add((user_id, item_id))

        for item_id in info.get("user_might_like", []):
            ensure_item(item_id)
            might_like.add((user_id, item_id))

    return {
        "users": [(uid, idx) for uid, idx in users.items()],
        "items": [(iid, title) for iid, title in items.items()],
        "interactions": list(interactions),
        "user_might_like": list(might_like),
    }


async def _bulk_load(conn: asyncpg.Connection, rows: dict) -> None:
    # Order matters: parents before children (foreign keys).
    await conn.copy_records_to_table(
        "users", records=rows["users"], columns=["user_id", "user_idx"]
    )
    await conn.copy_records_to_table(
        "items", records=rows["items"], columns=["item_id", "title"]
    )
    await conn.copy_records_to_table(
        "interactions", records=rows["interactions"], columns=["user_id", "item_id"]
    )
    await conn.copy_records_to_table(
        "user_might_like",
        records=rows["user_might_like"],
        columns=["user_id", "item_id"],
    )

    # Derive item_popularity from the watch matrix.
    await conn.execute("""
        INSERT INTO item_popularity (item_id, n)
        SELECT item_id, COUNT(DISTINCT user_id) AS n
        FROM interactions
        GROUP BY item_id;
        """)


async def _report(conn: asyncpg.Connection) -> None:
    tables = [
        "users",
        "items",
        "interactions",
        "user_might_like",
        "item_popularity",
    ]
    print("\nLoaded row counts:")
    for table in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"  {table:<20} {count:>8,}")


async def main() -> None:
    print(f"Reading dataset from: {settings.data_dir}")
    rows = _collect_rows()

    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        print("Applying schema...")
        await _apply_schema(conn)
        print("Bulk-loading tables...")
        await _bulk_load(conn, rows)
        await _report(conn)
    finally:
        await conn.close()
    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
