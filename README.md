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

**Requirements:** Python 3.9+, and the packages in `requirements.txt`
(`sentence-transformers`, `numpy`). Install:

```bash
pip install -r requirements.txt
```

Place the `patents_ipa*.json` data files in the project directory (or point the
scripts at their location).

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

| File               | Purpose                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------ |
| `patent_index.py`  | Core engine: `load_and_chunk`, `embed_chunks`, `PatentSearchEngine` (semantic + hybrid search, max-pooling), plus a CLI. |
| `demo.py`          | Scripted, readable demonstration of all search modes.                                                                    |
| `explore_data.py`  | Data-reconnaissance script (field coverage, types, length stats).                                                        |
| `requirements.txt` | Dependencies.                                                                                                            |
| `DECISIONS.md`     | Decision log — the reasoning behind each design choice.                                                                  |

---

## Where this goes next (Parts 2 & 3)

The chunk-level design already surfaces the core scaling tension: 640 patents
produced ~32K chunks (~50× multiplier), so 10M patents implies ~500M chunks. The
Part 2 design addresses this with a funnel — metadata pre-filtering, quantized
approximate-nearest-neighbor indexing for coarse retrieval, and a precise
chunk-level re-rank only on the surviving candidates — so chunk-level precision
becomes an affordable second phase rather than a corpus-wide cost. Candidate Part
3 enhancements include the section-weighting fix above, a cross-encoder re-ranker,
and evaluation of embedding quality against labeled prior-art pairs.
