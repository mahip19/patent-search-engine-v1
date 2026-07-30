# Patent Prior-Art Search Engine

A search engine that helps check if an invention idea already exists in patent data. Built for the ThinkStruct coding task. You type in what your idea is, and it finds the most similar existing patents.

---

## What it does

An inventor wants to know if their idea is already patented before they file. They type in keywords or a description, and the engine returns the most similar patents ranked by relevance.

It's a **search tool, not a legal tool** — it shows you the candidates, you decide if there's a conflict. That's how real prior-art tools work too.

---

## How it works

**1. Semantic search.**
Each patent gets broken into chunks (abstract, individual claims, description paragraphs). Each chunk gets turned into a vector using a sentence-transformer model. When you search, your query also becomes a vector, and we find the closest chunks by cosine similarity. This means it finds related patents even when they use completely different words.

**2. Max-pooling per patent.**
Instead of one big vector per patent, we score every chunk separately, then take each patent's best chunk score as its final score. This way a specific matching claim doesn't get buried by pages of unrelated text, and we can show you *which* passage actually matched.

**3. Hybrid filtering.**
You can add metadata filters on top of semantic search — classification prefix (like `B60B`), title substring, abstract substring. These are **pre-filters**: they narrow the pool *before* running similarity, so the math only runs on relevant chunks. This is faster and avoids the problem where post-filtering could accidentally remove all your results.

---

## Data

64 files × 10 patents = **640 patents → 32,439 chunks** (640 abstracts, 10,578 claims, 21,221 description paragraphs).

`detailed_description` is missing in 119/640 patents (18.6%). Everything else is always present. When a field is missing, we skip that section but still keep the patent — we never throw out a whole patent just because one field is empty.

---

## Results & timing

All on CPU:

- **Index build:** ~52s (one-time)
- **Search (no filter):** ~43ms
- **Search (B60C filter):** 32,439 → 17,378 chunks, ~17ms
- **Search (B60B + title "wheel"):** 32,439 → 8,191 chunks, ~40ms

Pre-filtering helps most when it cuts a big chunk of the pool. At small pool sizes the timing flattens because encoding the query takes a fixed amount of time no matter what. The real payoff is at scale — filtering millions down to thousands is where it matters.

---

## Known limitations

1. **Description chunks dominate.** 14 of 15 demo results matched on description, only 1 on a claim, 0 on abstract. Descriptions make up 65% of chunks so max-pooling gives them more chances to win. Also, natural-language queries are just closer in style to description text than to legal claim language. A fix would be to weight claim scores higher before max-pooling — not implemented yet.

2. **Truncation.** The model has a ~256 token limit. About 9.3% of chunks (mostly long description paragraphs) get cut off.

3. **No deduplication.** Patent families can file near-identical applications. The engine might return several very similar patents without grouping them.

---

## How to run

```bash
pip install -r requirements.txt
```

Put the `patents_ipa*.json` files in `data/patent_data_small/`.

```bash
# explore the data
python3 explore_data.py

# run a query
python3 patent_index.py --query "bicycle wheel spoke vibration"

# with filters
python3 patent_index.py --query "aerodynamic drag" --classification B60B --title-contains wheel

# limit results
python3 patent_index.py --query "..." --top-k 5

# run the full demo
python3 demo.py
```

---

## Files

| File | What it does |
|------|-------------|
| `patent_index.py` | Main engine — chunking, embedding, search, CLI |
| `demo.py` | Runs through all search modes with example queries |
| `explore_data.py` | Data exploration script (field stats, types, lengths) |
| `poc_metadata_store.py` | Part 2 PoC — Postgres metadata store with indexed filters |
| `DesignScale.md` | Part 2 design doc — scaling to 10M patents |
| `DecisionsLog.md` | Why I made each design choice |
| `requirements.txt` | Dependencies |

---

## Part 2 — Scaling

Two pieces:

**Design doc (`DesignScale.md`)** — how this engine would handle 10M patents. The main problem: 640 patents made ~32K chunks, so 10M patents means ~500M chunks (~768 GB of vectors). Can't brute-force that. The solution is a funnel: first filter by metadata (fast, uses DB indexes), then do approximate nearest-neighbor search over compact document-level vectors (fits in RAM), then do precise re-ranking with a cross-encoder only on ~100 survivors.

**PoC (`poc_metadata_store.py`)** — builds the Postgres metadata store from the design. Creates a patents table with b-tree indexes, loads data idempotently, runs filtered queries, and shows with `EXPLAIN ANALYZE` that Postgres uses the index (not a full table scan) for classification prefix lookups. Also prints a status dashboard with real data — total indexed, status counts, top classifications, freshness.

```bash
pip install psycopg2-binary
createdb patents
python3 poc_metadata_store.py
```

At 640 rows Postgres prefers a sequential scan (faster for tiny tables), so the PoC forces the index path to prove it works. At millions of rows the optimizer would pick the index on its own.
