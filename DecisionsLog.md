# Decision Log

This document records the key design decisions behind the search engine — what
the choice was, what alternatives I weighed, and (importantly) what evidence
resolved it. Several decisions were deliberately _deferred_ until data was
available rather than guessed up front; those are called out, because deciding
_when_ to commit was itself part of the process.

---

## 1. Scope: what does the engine actually do?

**Decision:** A prior-art / novelty **checker** that ranks and surfaces candidate
patents. The human makes the final novelty and infringement judgment.

**Alternatives considered:** Early on I mis-modeled the workflow as a tool for
_building_ a patent's claim list (find similar patents, then somehow incorporate
them). That was wrong: a patent's claims are the legally enforceable definition of
_its own_ invention, not a bibliography of similar patents.

**What resolved it:** Reasoning through what a similar-patent result _means_ to the
user — finding a near-identical existing patent is _bad news_ (the idea may not be
novel). That reframed the tool from "claim builder" to "prior-art checker," and it
fixed the success criterion: the engine only has to put the right candidates in
front of the user, not decide novelty (a much harder, arguably unsolvable, and
legally inappropriate target for an automated tool).

---

## 2. Inputs

**Decision:** Two query modes — short keywords, and a natural-language description
of the idea.

**Why:** These map onto the two things a real user does, and they correspond to two
different matching paradigms: keyword/lexical matching and semantic (meaning-based)
matching. The natural-language mode is the one that needs embeddings, because a
relevant patent may describe the same idea in entirely different words.

---

## 3. Output format

**Decision:** A ranked list of candidate patents, most-similar first, each with a
similarity score, metadata, and **the specific chunk (claim/paragraph) that
matched.**

**Why:** For a prior-art review, "which claim collides" is more useful than "this
patent is somewhat related." Showing the matching passage turns the result into
something the user can immediately act on.

---

## 4. Index granularity: per-patent vs. per-section

**Decision:** Per-section (chunk-level). Each abstract, each claim, and each
description paragraph is its own embedded chunk; patents are reassembled at ranking
time by **max-pooling** (a patent's score = its best chunk's score).

**Alternative:** One vector per patent (embed concatenated fields). Simpler, one
score per patent for free, fewer vectors — but it dilutes signal.

**What resolved it — measured evidence:** The data's own length statistics.
Abstracts median ~714 characters, claims ~4.5K, descriptions ~19K (max ~185K).
Concatenating and embedding as one vector would let a ~185K-character description
drown a ~714-character abstract and the actual claims. Per-section keeps each unit
sharp. At the current scale (~32K chunks) the extra complexity is cheap; the only
real cost (more vectors) is a scaling concern deferred to Part 2.

---

## 5. Which fields to embed

**Decision:** Embed all sections (abstract, claims, description), each tagged with
its section, so field choice can be revisited at query time without re-embedding.

**Reasoning:** Claims are the legally central field for novelty and had to be in.
Abstract is a clean, dense summary. Description is noisier and longer, and I was
initially unsure whether to include it. Rather than guess, I embedded everything
but tagged it — preserving the option to filter or down-weight sections later.

**Corroborating evidence:** The token-truncation measurement showed 9.3% of chunks
exceed the model's ~256-token window, and almost all of them are long description
paragraphs — i.e. the truncation self-limits to the field that matters least,
while claims and abstracts (which fit comfortably) are embedded in full. This made
"embed everything" cheap to defend.

---

## 6. Missing-data policy

**Decision:** Skip a missing section, never drop the whole patent.

**What resolved it — measured evidence:** `detailed_description` is missing in
18.6% of patents (119/640), but every patent has title, abstract, claims, and
classification. Since claims are the most novelty-relevant field and are always
present, dropping a patent for a missing description could hide a genuine prior-art
collision. Skipping just the absent section keeps every patent searchable on its
strongest fields.

---

## 7. Embedding model

**Decision:** `all-MiniLM-L6-v2` (384-dim, CPU-friendly, fast).

**Why:** Small and fast enough to build the whole index in ~52 s on CPU and answer
queries in tens of milliseconds, which is right for a Part 1 MVP over 640 patents.
Its ~256-token limit is a known tradeoff (see limitation on truncation) accepted in
exchange for speed and zero-GPU operation.

---

## 8. Hybrid search: pre-filter vs. post-filter

**Decision:** Pre-filter — apply metadata filters _before_ the cosine similarity
math.

**Why, on two axes:**

- _Performance:_ the expensive similarity step only runs on surviving chunks, so
  filtering to a small class does proportionally less work.
- _Correctness:_ post-filtering (rank first, then drop non-matching) can select a
  top-k _before_ applying the filter and then gut it — potentially returning far
  too few results, or none, even when valid matches exist deeper in the ranking.
  Pre-filtering draws the top-k from the already-valid pool by construction.

**Verification:** Across the three timed runs, a patent that survived every filter
kept an identical similarity score, confirming the filter acts as a gate on
_eligibility_ without contaminating the _ranking_.

---

## 9. Decisions I deferred or revised on evidence

This section is the honest core of the log — the places I intentionally did _not_
commit early, and one belief the data overturned.

- **Deferred: abstract+claims vs. embed-everything.** I refused to lock this in
  until I had run the engine and seen where matches actually came from. The
  "embed-everything-but-tag" approach meant deferring cost nothing. (Resolved in
  favor of embedding everything — see #5.)

- **Deferred: index granularity, until the length stats came back.** The
  per-section decision (#4) was made _because_ of measured field lengths, not on
  the assumption that descriptions are long.

- **Revised on evidence: "description is just noise."** My initial instinct was
  that descriptions were low-signal boilerplate to be down-weighted. The section
  match distribution overturned this: description chunks won **14 of 15** top
  results, claims 1, abstracts 0. Descriptions aren't noise — they're where
  natural-language queries actually land, because plain-prose queries are lexically
  closer to plain-prose descriptions than to claim legalese, and because
  descriptions have ~40× more chunks per patent than the abstract, giving
  max-pooling far more chances to find one strong hit.

  This created a real tension: the engine matches on descriptions ~93% of the time,
  yet a novelty check ultimately cares about **claims**. Rather than paper over it,
  I documented it as the top known limitation with a concrete proposed fix —
  **section weighting** (scale claim/abstract similarities up, or description down,
  before max-pooling) so a strong claim match can surface. I chose to document
  rather than implement for v1, because Part 1 is functionally complete and the
  fix is better validated with the labeled-relevance evaluation planned for Part 3
  than tuned by hand now.

---

## 10. Part 2 — scaling architecture: a retrieval funnel

**Decision:** A funnel — metadata pre-filter → quantized ANN coarse retrieval over
**document-level** vectors (in RAM) → cross-encoder re-rank over hydrated chunks
only on the ~100 survivors.

**Why:** The binding constraint at 10M patents is memory, not build time (patents
arrive in weekly batches, so indexing is an offline job). 500M chunk vectors ≈
768 GB won't fit in RAM, but 10M _document-level_ vectors quantized to int8 ≈
~4 GB will. So chunk-level precision — which Part 1 relies on — is too expensive to
run across the whole corpus, but is affordable as a _second phase_ on a small
survivor set. The funnel keeps Part 1's chunk-level, show-the-matching-claim
behavior while staying within a single-machine memory budget for the hot path.

**Acknowledged tradeoffs (not hidden):** Phase-1 recall caps everything downstream;
the cross-encoder is the cost/latency driver; unfiltered queries force cross-shard
scatter-gather; and updating a quantized, sharded ANN index is genuinely awkward
(mitigated by shadow-index-and-swap). These are documented in the design doc's
challenges section per the task's guidance to pick something simple and name its
weaknesses.

## 11. Part 2 — proof-of-concept: which piece to build

**Decision:** Build the **PostgreSQL metadata store** with indexed hybrid
pre-filtering, plus a thin status view fed by real data.

**Alternatives considered (from the task's menu):**

- _Status dashboard from dummy data_ — satisfies the monitoring ask but proves no
  real pipeline piece; disconnected from the actual engine.
- _Real ANN/FAISS index_ — highest-fidelity, but beyond the depth I could confidently
  defend in review, and over-engineered for a 15-minute PoC.
- _Containerize Part 1_ — low signal; plumbing, not system design.
- _Postgres metadata store_ — chosen: simple, within depth, and a **real component
  from the design doc** that proves a concrete claim.

**Why this one:** It directly fixes a real Part 1 limitation. Part 1's hybrid filter
scanned every chunk in Python; at scale that is the bottleneck. Pushing the filter
into an indexed Postgres column turns it into a fast lookup. I combined it with the
status-view idea so the "dashboard" reads _real_ counts (indexed total, status
breakdown, top classifications, freshness) rather than dummy data — satisfying the
design doc's "track contents & status" requirement with a live component. This makes
a coherent Part 1 → Part 2 story: limitation identified → fix designed → fix built
and proven.

**What I proved, and an honest nuance:** `EXPLAIN ANALYZE` shows a Bitmap Index Scan
on the classification index for `LIKE 'B60B%'` (Postgres rewrites the prefix into a
range walk). At 640 rows the optimizer would actually prefer a sequential scan —
correctly, because the table is tiny — so I forced the index path with
`enable_seqscan=off` purely to demonstrate it works; at millions of rows the
optimizer chooses the index on its own. Naming _why_ the optimizer behaves this way,
rather than pretending the tiny-table result is production-representative, is the
honest framing. I also hit and handled the standard Postgres gotcha that `LIKE`
prefix queries need `text_pattern_ops` on the index to use it under default
collations.

---

## 12. Part 3 — which enhancements to pick

**Decision:** Two enhancements — two-phase re-ranking, and evaluation + fine-tuning.

**Why these two:**

- _Two-phase re-ranking_ builds straight on the Part 2 design (it's the "second
  phase" of that funnel) and was a chance to test whether it fixes the Part 1
  description-dominance limitation.
- _Evaluation_ was the missing piece everywhere else: up to this point I could only
  _say_ results looked good. Evaluation turns that into actual numbers, and it also
  lets me measure whether re-ranking and fine-tuning really help.

I skipped the other two options on purpose: "efficiency / large data" and "machine
translation" both need extra data samples I'd have to request, which didn't fit a
same-day submission.

## 13. Part 3 — how I set up the evaluation (avoiding two traps)

**Decision:** Grade the engine using each patent's own abstract as the query, with
the correct answer being that same patent.

**Two traps I had to avoid, or the numbers would be fake:**

1. _The mirror trap._ If the query is an abstract and that abstract is also in the
   search index, the patent matches itself perfectly and every score looks great.
   Fix: the eval index holds only claims and descriptions — no abstracts — so the
   engine has to find the patent through different text.
2. _The studying-the-test trap._ A fine-tune only means something if it's tested on
   patents it didn't train on. Fix: an 80/20 train/test split, with training pairs
   from the train half and all scoring on the held-out test half.

**How I read the results honestly:**

- Fine-tuning genuinely helped (Recall@1 84% → 92%), which beat my expectation — I
  assumed a tiny fine-tune might do nothing. The honest caveat is that the training
  goal (abstract ↔ claim) closely matches what the test measures, so the model was
  well-suited to this exact metric.
- I did **not** claim the re-ranker "lost." Its column was measured on a smaller
  30-query subset, so it's not on the same scale as the others — comparing them
  directly would be misleading. I said that plainly rather than spinning it.
- The baseline landing at 0.836 (not 1.0) was the proof the mirror trap was
  actually avoided.

---

## Summary

The decisions that most shaped the system: framing it as a _checker_ (not a claim
builder), choosing _per-section_ granularity to protect claim signal, and using
_pre-filtered_ hybrid search for both speed and correctness. For scale (Part 2), the
same pre-filter idea became a Postgres-backed indexed lookup, and the query path
became a funnel that defers expensive re-ranking to a small survivor set. For Part 3,
I built that second phase for real and added an evaluation so I could put numbers on
everything. The habit I tried to keep throughout: **wait for data before deciding,
let the measurements correct me, and report what actually happened — including the
results that didn't match my guess.**
