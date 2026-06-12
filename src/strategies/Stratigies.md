# Strategies

This folder has the different ways the app can answer a user and recommend
movies. Every way is called a "strategy". They all do the same job (talk to the
user and suggest movies), but they work in a different way. The app can use any
of them. This makes it easy to compare them and see which one is better.

All strategies share two things:
- the **LLM** (the language model that writes the answer), and
- the **database pool** (the connection to Postgres where the movie data is).

The only difference between strategies is **how they build the context** and
**how many times they call the model**.

## The shared base

`base.py` has the class `RecommendationStrategy`. Every strategy comes from this
class. It gives them the model, the database, and a small helper called
`_titles` that changes movie ids into movie names. Each strategy must have a
`stream` method that sends back the answer piece by piece (token by token), so
the user can read it while it is still being written.

## The three strategies
### 1. Few-shot (the simple one) — `fewShot/`

This is the baseline. It does **not** look in the database for movies. It only
uses what the model already knows from its training. We give the model one
example conversation to show it the good style, plus the list of movies the user
watched. Then the model answers in one call.

### 2. RAG (the grounded one) — `rag/`

RAG means "get data first, then write the answer". Here the code runs the
**collaborative filtering** (CF) search one time. CF looks at the movies the user
watched and finds good candidate movies from real data. We put these real movies
into the prompt, and the model picks the best ones and explains them in one call.

### 3. Agent (the smart one) — `agent/`

The agent is the most advanced. Here the **model decides** what to do. We give it
some tools, and it can call them when it wants, more than one time, step by step.
It thinks, calls a tool, looks at the result, and continues. This is good for
harder talks, like when the user changes the request in the middle.

The agent has two main tools to find movies:
- **recommend_candidates** — finds movies from the user's **own history** (what
  this user watched and liked).
- **recommend_from_similar_users** — finds movies from **other users with
  similar taste** (people who watched the same movies enjoyed these too).

And two helper tools:
- **search_movies** — takes a movie name the user said and finds its id in the
  database (it is okay if the name has small spelling mistakes).
- **similar_movies** — finds movies that are like one specific movie.

The agent follows a simple plan:
1. Say hello. Ask the user which movies they liked the most.
2. If the user **names** some movies, use `search_movies` to find them in the
   database, then use `recommend_candidates` with those movies.
3. If the user does **not** name any movie, use their history instead: get
   candidates from their last watched movies, and also use
   `recommend_from_similar_users` to add picks from people with similar taste.

In every case, the agent only suggests **real** movies that the tools returned.
It never invents a title.

## RAG vs Agent in one line

RAG searches one time and the **code** controls it (get data, then answer). The
agent searches when **it** wants and controls it by itself (think, act, look,
repeat).
