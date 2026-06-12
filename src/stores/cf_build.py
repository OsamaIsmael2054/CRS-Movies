import asyncio

import asyncpg
import numpy as np
from scipy.sparse import csr_matrix

from helpers.config import settings


async def _fetch_interactions(conn: asyncpg.Connection) -> list[asyncpg.Record]:
    return await conn.fetch("SELECT user_id, item_id FROM interactions")


def _build_matrix(
    rows: list[asyncpg.Record],
) -> tuple[csr_matrix, list[str]]:
    """Return a binary CSR user x item matrix and the column->item_id list."""
    user_index: dict[str, int] = {}
    item_index: dict[str, int] = {}
    item_ids: list[str] = []
    user_pos: list[int] = []
    item_pos: list[int] = []

    for user_id, item_id in rows:
        u = user_index.get(user_id)
        if u is None:
            u = user_index[user_id] = len(user_index)
        i = item_index.get(item_id)
        if i is None:
            i = item_index[item_id] = len(item_index)
            item_ids.append(item_id)
        user_pos.append(u)
        item_pos.append(i)

    data = np.ones(len(user_pos), dtype=np.float32)
    matrix = csr_matrix(
        (data, (user_pos, item_pos)),
        shape=(len(user_index), len(item_index)),
        dtype=np.float32,
    )
    matrix.data[:] = 1.0  # collapse any duplicate (user, item) entries to binary
    return matrix, item_ids


def _top_neighbors(
    matrix: csr_matrix, item_ids: list[str], top_m: int
) -> list[tuple[str, str, float]]:
    """Top-M cosine neighbors per item from the sparse co-occurrence product."""
    # Co-occurrence counts C = X^T X (items x items, sparse). Diagonal = item freq.
    cooc = (matrix.T @ matrix).tocsr()
    norms = np.sqrt(cooc.diagonal())
    norms[norms == 0] = 1.0  # guard (shouldn't happen: every item has >=1 user)

    indptr, indices, values = cooc.indptr, cooc.indices, cooc.data
    records: list[tuple[str, str, float]] = []

    for i in range(cooc.shape[0]):
        start, end = indptr[i], indptr[i + 1]
        cols = indices[start:end]
        scores = values[start:end] / (norms[i] * norms[cols])

        keep = cols != i  # drop self-similarity
        cols, scores = cols[keep], scores[keep]
        if cols.size == 0:
            continue

        if cols.size > top_m:
            top = np.argpartition(scores, -top_m)[-top_m:]
            cols, scores = cols[top], scores[top]

        src = item_ids[i]
        for col, score in zip(cols, scores):
            records.append((src, item_ids[col], float(score)))

    return records


async def main() -> None:
    conn = await asyncpg.connect(dsn=settings.database_url)
    try:
        print("Fetching interactions...")
        rows = await _fetch_interactions(conn)
        print(f"  {len(rows):,} interactions")

        matrix, item_ids = _build_matrix(rows)
        print(
            f"Building item-item similarity ({len(item_ids):,} items, "
            f"top-{settings.cf_top_m})..."
        )
        records = _top_neighbors(matrix, item_ids, settings.cf_top_m)

        print(f"Writing {len(records):,} neighbor rows...")
        await conn.execute("TRUNCATE item_similarity")
        await conn.copy_records_to_table(
            "item_similarity",
            records=records,
            columns=["item_a", "item_b", "score"],
        )

        count = await conn.fetchval("SELECT COUNT(*) FROM item_similarity")
        print(f"Done. item_similarity rows: {count:,}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
