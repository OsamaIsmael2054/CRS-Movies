# Movies-CRS

A conversational movie recommender on the LLM-Redial *Movie* dataset, served as
a streaming async FastAPI endpoint. Retrieval is driven by collaborative
filtering over the interaction matrix; the LLM re-ranks and explains a small
CF-generated candidate set. Three approaches are implemented — few-shot (`POST
/chat` `mode=fewshot`), CF-grounded RAG (`mode=rag`), and a tool-calling agent
(`mode=agent`).

## Documentation

More detailed, easy-to-read docs live next to the code they describe:

- [`src/stores/Database.md`](src/stores/Database.md) — how the database is built:
  the tables, loading the dataset (`load.py`), building the CF similarity
  (`cf_build.py`), and the read functions used at query time.
- [`src/strategies/Stratigies.md`](src/strategies/Stratigies.md) — the three
  recommendation strategies (few-shot, RAG, agent), the agent's tools, and how
  they differ.

## Requirements

- **Python 3.13** (the project targets 3.13; 3.10+ works).
- **Docker** + Docker Compose (runs PostgreSQL 18).
- **[Ollama](https://ollama.com)** running locally on `:11434` with a model
  pulled (default `gemma4:12b`).

```bash
ollama pull gemma4:12b      # then make sure `ollama serve` is running
```

## 1. Start and load the database

PostgreSQL runs in Docker; the dataset is loaded into it once. The source files
live in [`src/assets/Movie/`](src/assets/Movie) and are read only by the loader.

```bash
# --- one-time: create the env files from the templates ---
cp docker/env/.env.postgres.example docker/env/.env.postgres
cp docker/env/.env.app.example      docker/env/.env.app

# --- start Postgres (waits until healthy) ---
cd docker && docker compose up -d && cd ..

# --- Python env + dependencies ---
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# --- upload the dataset into Postgres + build CF similarity ---
python -m src.stores.load        # applies db/schema.sql and bulk-loads all tables
python -m src.stores.cf_build    # computes item-item similarity (item_similarity)
```

`load` prints the row counts per table; `cf_build` prints the number of
neighbor rows written. Both are re-runnable (the schema is dropped/recreated).

## 2. Start the project

**Locally (recommended — uses your Python 3.13):**

```bash
source .venv/bin/activate
uvicorn src.main:app --reload --port 8000
```

**Or fully containerized** (builds the app image, reaches Ollama on the host):

```bash
cd docker && docker compose --profile app up -d --build
```

### API usage

```bash
# health
curl http://localhost:8000/health

# stream a recommendation (mode = fewshot | rag | agent)
curl -N -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
        "message": "I love old classic musicals. What should I watch next?",
        "history": ["6300159140", "6300215695", "6301977343"],
        "user_id": "A30Q8X8B1S3GGT",
        "mode": "rag"
      }'
```

`history` is a list of catalog item ids the user has watched; `mode` selects the
strategy. Responses stream token-by-token.

## Two prompt changes that increase recommendation accuracy

Both changes are applied to the **RAG** prompt (where the model re-ranks a fixed
CF candidate list) and are evaluated as an ablation in via the `rag_dislike`
and `rag_cot` methods, measured against the plain `rag` baseline with Recall@k /
Hit@k / NDCG@k on held-out conversations.

### 1. Explicit dislike-avoidance (negative signal in the prompt)

**Change.** Inject the user's disliked titles into the prompt and add an
instruction to *not* recommend anything similar in genre or style:

> "The user has disliked some movies; do not recommend anything similar in genre
> or style to those." … `I did NOT enjoy: <disliked titles>.`

**Why it raises accuracy.** The baseline prompt only describes positive taste, so
the model can surface candidates that match a liked theme but collide with a
known dislike (e.g. recommending a slasher to someone who liked thrillers but
dislikes horror). Stating the negatives turns a one-sided preference signal into
a two-sided one: the model actively prunes near-misses, which removes
false-positive recommendations from the top-k and lifts precision/recall at the
cutoff. (In the retrieval layer the same dislikes also subtract `item_similarity`
mass via `cf.recommend(..., disliked_ids=...)`, so the prompt change and the
candidate set are consistent.)

### 2. Chain-of-thought before choosing

**Change.** Instruct the model to reason step by step about overlap before
committing to picks:

> "Before choosing, reason step by step about genre, era, and style overlap with
> the user's taste, then give your picks."

**Why it raises accuracy.** The candidate list is behaviorally grounded but
unordered with respect to the user's stated taste. Forcing the model to first
articulate *why* each candidate fits (genre/era/style) makes the final ranking a
consequence of explicit comparison rather than position or surface salience. This
reduces arbitrary selection among similar candidates and pushes the genuinely
best-matching item higher, improving NDCG@k in particular (rank-sensitive),
alongside Recall/Hit@k.

> Note: these are *prompt-level* CoT instructions, distinct from the model's
> native reasoning, which is disabled (`ollama_think=False`) so content streams
> immediately — see `src/clients/ollama.py`.
