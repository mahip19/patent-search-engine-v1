# Patent Prior-Art Search Engine

A semantic + hybrid search engine over patent-application data, built for the
ThinkStruct coding task (Part 1). It lets a user check whether an invention
idea already appears in existing patents — a **prior-art / novelty check**.

---

## Problem statement

The problem I chose to solve: **an inventor wants to know whether their idea is
already patented before they file.**

Concretely, the user has either (1) a few keywords or (2) a short natural-language
description of their idea, and wants to see the existing patents most similar to
it. Finding a very similar patent is _bad news_ — it means the idea may not be
novel, or building it could risk infringement.

The engine's job is therefore **retrieval and ranking, not judgment.** It surfaces
the most relevant candidate patents (and the specific passage that matched) and
leaves the final novelty/infringement call to the human — because deciding
novelty is a legal determination the tool shouldn't fake.

This mirrors how real prior-art tools work: the user pastes an idea, a claim, or
an abstract, and the system returns ranked candidates to review.

---

## Approach

**1. Semantic search (meaning, not keywords).**
Every patent is broken into chunks, each chunk is embedded into a vector with a
sentence-transformer model, and a query is answered by cosine similarity in that
vector space. This finds patents that mean the same thing even when they share no
words — e.g. the query _"bicycle wheel spoke that reduces vibration"_ returns
_"BICYCLE HUB AND SPOKE ARRANGEMENT"_ as its top hit despite little word overlap.

**2. Chunk granularity + max-pooling.**
Rather than squashing a whole patent into one vector, each patent becomes several
chunks — one per abstract, one per claim, one per description paragraph — each
tagged with its source section. At query time the engine scores every chunk, then
**max-pools to the patent level**: each patent's score is that of its single
best-matching chunk. This keeps signal sharp (a specific claim isn't diluted by
pages of boilerplate) and lets the engine show the user _exactly which passage_
triggered the match.

**3. Hybrid search (semantic + hard filters).**
The engine supports combining semantic ranking with exact metadata filters:
classification-code prefix (e.g. `B60B`), a substring in the title, and a
substring in the abstract. Filters are applied as **pre-filters** — the candidate
set is narrowed _before_ the similarity math runs, which is both faster (the
expensive step touches fewer chunks) and more correct (the top-k is drawn from
the already-valid pool, so a filter can never silently empty out a result list
the way post-filtering can).

---

## Data handling

The sample is 64 files × 10 patents = **640 patents**, producing **32,439 chunks**
(640 abstract, 10,578 claim, 21,221 description).

**Missing fields:** `detailed_description` is absent in 18.6% of patents
(119/640); all other fields are present 100% of the time. Policy: **skip the
missing section, never drop the patent.** A patent with no description is still
fully indexed on its claims and abstract — which matters, because claims are the
most novelty-relevant field and dropping a patent could hide a genuine prior-art
collision.

---

## Results & timing

Measured on CPU over the 640-patent sample:

- **Index build (one-time):** ~52 s (model load + embedding 32,439 chunks).
- **Search latency (baseline, no filter):** ~40–53 ms per query.
- **Hybrid search, pool shrinkage & timing:**
  - No filter: 32,439 chunks → ~43 ms
  - `classification=B60C`: 32,439 → 17,378 chunks → ~17 ms
  - `classification=B60B` + `title~"wheel"`: → 8,191 chunks → ~40 ms

**Efficiency commentary:** pre-filtering roughly halves latency when it roughly
halves the candidate pool (the B60C case). But at very small pool sizes the
timing flattens out or even ticks up, because a fixed per-query cost — encoding
the query into a vector — dominates once the corpus-scan cost becomes trivial.
The takeaway is that pre-filtering's payoff is **at scale**: over millions of
patents the similarity scan dominates, and filtering from millions down to
thousands is the difference between a usable and unusable engine. (This is the
bridge to the Part 2 scaling design.)

---

## Known limitations

1. **Description chunks dominate matches.** Across the demo runs, 14 of 15 top
   results matched on a _description_ chunk, 1 on a claim, 0 on an abstract —
   even though **claims** are the legally central field for a novelty check. The
   likely causes are (a) descriptions are 65% of all chunks (~40 paragraphs per
   patent vs. ~16 claims vs. 1 abstract), so max-pooling gives them far more
   chances to produce one high-scoring chunk, and (b) natural-language queries
   are lexically closer to plain-prose descriptions than to dense claim legalese.
   **Proposed fix (not implemented in v1): section weighting** — scale claim and
   abstract similarities up (or description down) before max-pooling, so a strong
   claim match can surface above a merely-well-matched description paragraph.

2. **Long-chunk truncation.** The embedding model (`all-MiniLM-L6-v2`) has a
   ~256-token limit; 9.3% of chunks (almost all long description paragraphs)
   exceed it and are truncated, so only their opening portion is embedded.

3. **No near-duplicate handling.** Patent families file near-identical
   applications; the engine can return several near-duplicates in one result set,
   as there is no de-duplication step.

---

## How to run

**Requirements:** Python 3.9+, and the packages in `requirements.txt`. Install:

```bash
pip install -r requirements.txt
```

Place the `patents_ipa*.json` data files in `data/patent_data_small/`.

**Explore the data (optional, reconnaissance):**

```bash
python3 explore_data.py
```

**Run a single query via the CLI:**

```bash
# pure semantic
python3 patent_index.py --query "bicycle wheel spoke vibration"

# with a classification filter
python3 patent_index.py --query "aerodynamic drag" --classification B60B

# hybrid: classification + title substring
python3 patent_index.py --query "aerodynamic drag" --classification B60B --title-contains wheel

# limit results
python3 patent_index.py --query "..." --top-k 5
```

**Run the guided demo (recommended — mirrors the screen recording):**

```bash
python3 demo.py
```

The demo runs a pure-semantic query, the same query with a classification
filter, a two-filter hybrid query, and an empty-result case, printing pool
sizes and timings for each.

---

## Project structure

| File                    | Purpose                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `patent_index.py`       | Core engine: `load_and_chunk`, `embed_chunks`, `PatentSearchEngine` (semantic + hybrid search, max-pooling), plus a CLI.                      |
| `demo.py`               | Scripted, readable demonstration of all search modes.                                                                                         |
| `explore_data.py`       | Data-reconnaissance script (field coverage, types, length stats).                                                                             |
| `app.py`                | Flask web UI — serves a browser-based search interface at `localhost:5001`.                                                                    |
| `static/index.html`     | Frontend for the web UI (single self-contained HTML file, no build step).                                                                     |
| `poc_metadata_store.py` | **Part 2 proof-of-concept:** PostgreSQL metadata store with indexed hybrid pre-filtering (`EXPLAIN ANALYZE`-verified) and a live status view. |
| `DesignScale.md`        | **Part 2 design doc:** how the engine scales to 10M patents (components, pipelines, cost, error handling, monitoring, challenges).            |
| `rerank.py`             | **Part 3:** two-phase search — Part 1 retrieval + a cross-encoder re-ranker.                                                                  |
| `evaluate.py`           | **Part 3:** evaluation (Recall@1/@10, MRR) + a small fine-tune of the embedding model.                                                        |
| `requirements.txt`      | Dependencies.                                                                                                                                 |
| `DecisionsLog.md`       | Decision log — the reasoning behind each design choice.                                                                                       |

---

## Part 2: Scaling

Two deliverables here.

**Design doc (`DesignScale.md`)** covers how this would work at 10M patents.

The core problem: 640 patents already make ~32K chunks, so 10M patents would mean ~500M chunks (~768 GB of vectors). That doesn't fit in memory. The solution is a funnel:
- Filter by metadata first (fast, uses DB indexes)
- Run approximate nearest neighbor search on compact document level vectors (fits in RAM)
- Only run the expensive cross encoder re-rank on ~100 survivors

The doc also covers ingestion pipelines, cost estimates, error handling, monitoring, and the main risks.

**PoC (`poc_metadata_store.py`)** builds one real piece from that design: a Postgres metadata store.

What it does:
- Creates a `patents` table with b-tree indexes for classification prefix lookups
- Loads all 640 patents idempotently (ON CONFLICT DO NOTHING)
- Runs filtered queries and shows `EXPLAIN ANALYZE` proving Postgres uses the index, not a full table scan
- Prints a status dashboard with real data (total indexed, top classifications, freshness)

At 640 rows Postgres would normally prefer a sequential scan (faster for tiny tables), so the PoC forces index usage to prove it works. At real scale the optimizer picks the index on its own.

```bash
pip install psycopg2-binary
# defaults to postgresql://localhost/patents, override with DATABASE_URL
python3 poc_metadata_store.py
```

## Part 3: Enhancements

I picked **two phase search (re-ranking)** and **evaluation + fine-tuning**.

Why these two: Part 1's biggest weakness was that description chunks dominated results over claims, which are the legally important part. Re-ranking fixes this because a cross encoder reads query and chunk together and can recognize claim relevance better. Evaluation lets me actually measure if things improved, and fine-tuning teaches the model to connect abstract style queries with claim language.

### Enhancement 1: Re-ranker (`rerank.py`)

Adds a second pass after Part 1's search:
- Phase 1: the fast bi-encoder grabs top 50 candidates
- Phase 2: a cross encoder scores each candidate by reading the query and patent text together (not as separate vectors), then re-sorts by that score

What I saw:
- Top result stayed the same, but 4 of the top 5 changed as more relevant patents got pulled up
- Phase 2 was ~35x slower (2.1s vs 59ms), which is why the Part 2 design only runs it on a small survivor set

```bash
python3 rerank.py
```

### Enhancement 2: Evaluation + fine-tuning (`evaluate.py`)

I needed ground truth without hand labeling. The trick: use each patent's abstract as a query, and the correct answer is that same patent. To prevent cheating, the eval index has no abstract chunks (only claims and descriptions).

Setup:
- 80/20 train/test split (512 train, 128 test, fixed seed)
- Three evaluations on the test set: (A) baseline bi-encoder, (B) baseline + cross encoder rerank on 30 queries, (C) fine-tuned bi-encoder
- Fine-tuning uses (abstract, claim) pairs from train patents with MultipleNegativesRankingLoss, 1 epoch

Results (128 test patents):

| Metric    | Baseline | + Re-rank (30 q) | Fine-tuned |
| --------- | -------- | ---------------- | ---------- |
| Recall@1  | 0.836    | 0.700            | **0.922**  |
| Recall@10 | 0.977    | **1.000**        | 0.992      |
| MRR       | 0.889    | 0.815            | **0.951**  |

Takeaways:
- Fine-tuning bumped Recall@1 from 84% to 92% after ~100s of training on ~4,000 pairs
- The re-rank column was measured on only 30 queries so it's not directly comparable to the others
- Baseline being 0.836 (not 1.0) confirms the "no abstracts in index" safeguard worked

```bash
python3 evaluate.py
```

## Additional feature: Web UI

A small browser based search interface on top of the Part 1 engine.

- `app.py` is a Flask backend that builds the `PatentSearchEngine` once on startup and exposes a `/api/search` endpoint
- `static/index.html` is the frontend (single self-contained file, no build step)
- Supports the same hybrid search: query, classification prefix, and title filter
- Shows results with the matched section, classification badge, and the passage that matched

Run it:

```bash
python3 app.py
# then open http://localhost:5001
```

The index build takes ~52s on startup. After that, searches run in the browser and the first query is a bit slower while the model warms up.
