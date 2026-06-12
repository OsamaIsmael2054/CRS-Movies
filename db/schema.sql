-- Movies-CRS schema. Re-runnable: drops then recreates everything.
-- Derived from the LLM-Redial Movie dataset (item_map / user_ids /
-- final_data.jsonl). See plan.md for the source->table map.

DROP TABLE IF EXISTS item_similarity CASCADE;
DROP TABLE IF EXISTS item_popularity CASCADE;
DROP TABLE IF EXISTS user_might_like CASCADE;
DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS items CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Catalog of users (user_ids.json: user_id -> dense index).
CREATE TABLE users (
    user_id  TEXT PRIMARY KEY,
    user_idx INTEGER UNIQUE NOT NULL
);

-- Catalog of movies (item_map.json: item_id -> title).
CREATE TABLE items (
    item_id TEXT PRIMARY KEY,
    title   TEXT NOT NULL
);

-- The watch matrix (final_data.history_interaction). Powers CF.
CREATE TABLE interactions (
    user_id TEXT NOT NULL REFERENCES users(user_id),
    item_id TEXT NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (user_id, item_id)
);
CREATE INDEX idx_interactions_user ON interactions(user_id);
CREATE INDEX idx_interactions_item ON interactions(item_id);

-- Per-user ground truth for eval (final_data.user_might_like).
CREATE TABLE user_might_like (
    user_id TEXT NOT NULL REFERENCES users(user_id),
    item_id TEXT NOT NULL REFERENCES items(item_id),
    PRIMARY KEY (user_id, item_id)
);

-- Derived: how many distinct users interacted with each item (cold-start fallback).
CREATE TABLE item_popularity (
    item_id TEXT PRIMARY KEY REFERENCES items(item_id),
    n       INTEGER NOT NULL
);
CREATE INDEX idx_item_popularity_n ON item_popularity(n DESC);

-- Derived (cf_build.py): top-M item-item neighbors by similarity.
CREATE TABLE item_similarity (
    item_a TEXT NOT NULL REFERENCES items(item_id),
    item_b TEXT NOT NULL REFERENCES items(item_id),
    score  REAL NOT NULL,
    PRIMARY KEY (item_a, item_b)
);
CREATE INDEX idx_item_similarity_a ON item_similarity(item_a);
