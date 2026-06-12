# Database

This folder builds and reads the database. The database is **PostgreSQL** and it
runs inside Docker. We put all the movie data inside it one time, and then the
app reads from it when a user asks for a recommendation.

The data comes from the LLM-Redial *Movie* dataset. The source files are in
`src/assets/Movie/`. We only read these files **once**, when we load the data.
After that, the app uses the database, not the files.

## The tables

The full table design is in `db/schema.sql`. Here are the tables in simple words:

- **users** — the list of all users. Each user has an id and a number.
- **items** — the list of all movies. Each movie has an id and a title (name).
  The dataset has no genre, no actors, no plot — only the title.
- **interactions** — the "watch matrix". One row means "this user watched this
  movie". This is the most important table, because it shows the behavior of the
  users. The recommendations are built from it.
- **user_might_like** — extra ground truth. Movies that a user may like. We use
  this only to test (evaluate) how good the recommendations are.
- **item_popularity** — for each movie, how many users watched it. We use this
  when we have no other information (cold start), to suggest popular movies.
- **item_similarity** — for each movie, the movies that are most similar to it.
  This is not in the dataset; we compute it ourselves (see below).

## The files in this folder

### `database.py` — the connection

This is the door to the database.
- `create_pool()` makes a **pool** of connections. A pool keeps some connections
  open and ready, so many requests can use the database at the same time without
  waiting. The web app uses this.
- `connect()` opens **one** connection. The small one-time scripts (like the
  loader) use this.

### `load.py` — put the data in (run one time)

This script fills the database from the dataset files. Run it with:

```bash
python -m stores.load
```

What it does, step by step:
1. Apply the schema from `db/schema.sql` (this drops the old tables and creates
   new empty ones, so the script is safe to run again).
2. Read the source files: `item_map.json` (movies), `user_ids.json` (users), and
   `final_data.jsonl` (the history of each user and the "might like" movies).
3. The data is a little dirty. Some movie ids or user ids appear in the history
   but are missing from the main lists. So the script adds them: a missing movie
   gets its id as the title, a missing user gets a new number. This keeps the
   foreign keys valid.
4. Bulk-load all the rows into the tables. It loads parents first (users, items),
   then children (interactions, user_might_like), because of the foreign keys.
5. Build `item_popularity` with one SQL query: count how many users watched each
   movie.
6. Print the row count of each table, so you can check it worked.

### `cf_build.py` — build the similarity (run after the loader)

CF means **collaborative filtering**: "people who watched the same movies as you
also liked these". This script computes which movies are similar to which, and
saves the result in the `item_similarity` table. Run it with:

```bash
python -m stores.cf_build
```

What it does:
1. Read all the rows from `interactions`.
2. Build a big sparse matrix: rows are users, columns are movies, and a cell is 1
   if the user watched the movie. It is "sparse" because most cells are 0 (each
   user watches only a few movies), so we only store the 1s to save memory.
3. Compute **cosine similarity** between movies. Two movies are similar when the
   same users watched both of them. The math is one matrix multiply.
4. For each movie keep only the **top-M** most similar movies (M is a setting,
   default 50). We do not keep all of them, because that would be too many rows.
5. Save these neighbor rows into `item_similarity`.

We do this heavy work **once**, offline. At query time the app only needs a fast,
simple lookup in this table. That keeps the API quick.

### `cf.py` — read the recommendations (used by the app)

This file has the functions the strategies call at request time. They are simple,
fast SQL lookups, not heavy math:
- `recommend(...)` — **item-based CF**. Take the movies the user watched and
  liked, look them up in `item_similarity`, add the scores, remove movies they
  already saw, and return the best new movies. If we know nothing about the user
  (cold start), it returns popular movies from `item_popularity`.
- `similar(item_id, ...)` — the movies most similar to **one** movie.
- `recommend_via_users(...)` — **user-based CF**. Find the users whose history
  overlaps this user the most (similar taste), then return the movies those
  neighbor users watched but this user did not. This one is computed live from
  `interactions`, so it needs no extra table.

### `catalog.py` — search by name

When a user types a movie **name** (maybe with a spelling mistake), this file
finds the matching movie id in the `items` table using fuzzy matching. The
strategies use the id after that.

## The normal order to run things

```bash
cd docker && docker compose up -d && cd ..   # 1. start Postgres
python -m stores.load                     # 2. load the data (one time)
python -m stores.cf_build                 # 3. build item_similarity (one time)
```

After these three steps the database is ready and the app can serve
recommendations.
