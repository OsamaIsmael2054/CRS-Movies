-- Movies-CRS schema. Re-runnable: drops then recreates everything.
-- Derived from the LLM-Redial Movie dataset (item_map / user_ids /
-- final_data.jsonl / Conversation.txt). See plan.md for the source->table map.

DROP TABLE IF EXISTS item_similarity CASCADE;
DROP TABLE IF EXISTS item_popularity CASCADE;
DROP TABLE IF EXISTS conversation_items CASCADE;
DROP TABLE IF EXISTS conversations CASCADE;
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

-- One row per conversation. conversation_id is the global dialogue index
-- shared with Conversation.txt; turn_index is its 1-based position for the user.
CREATE TABLE conversations (
    conversation_id INTEGER PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(user_id),
    turn_index      INTEGER NOT NULL,
    dialogue        TEXT
);
CREATE INDEX idx_conversations_user ON conversations(user_id);

-- Normalized user_likes / user_dislikes / rec_item per conversation.
CREATE TABLE conversation_items (
    conversation_id INTEGER NOT NULL REFERENCES conversations(conversation_id),
    item_id         TEXT NOT NULL REFERENCES items(item_id),
    role            TEXT NOT NULL CHECK (role IN ('like', 'dislike', 'rec')),
    PRIMARY KEY (conversation_id, item_id, role)
);
CREATE INDEX idx_conversation_items_role ON conversation_items(role);

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
