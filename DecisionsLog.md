# Decision Log

Why I made each design choice, what I considered, and what actually convinced me.

---

## 1. What the engine does

**Decision:** It's a prior-art checker — finds similar patents so you can review them. The human decides if there's a novelty conflict.

I initially thought of it as a tool to help *build* patent claims, but that didn't make sense. A patent's claims define its own invention, they're not a bibliography. Once I realized that finding a similar patent is *bad news* (means your idea might not be novel), the framing clicked: the engine just needs to surface good candidates, not make legal judgments.

---

## 2. Query types

**Decision:** Support both short keywords and natural-language descriptions.

These are the two things a user actually does, and they need different matching: keywords work with lexical matching, but a description like "quieter ride on rough pavement" needs semantic matching to find tire noise patents that use totally different words.

---

## 3. Showing the matching passage

**Decision:** Each result includes the specific chunk (claim/paragraph) that triggered the match, not just "this patent is related."

For a prior-art review, knowing *which claim* might collide is way more useful than a vague similarity score.

---

## 4. Per-section chunking vs. one vector per patent

**Decision:** Break each patent into chunks (one per abstract, one per claim, one per description paragraph) and max-pool at query time.

The alternative was to concatenate everything into one vector per patent. Simpler, but the data showed why it wouldn't work well: abstracts are ~714 chars, claims ~4.5K, descriptions can be up to ~185K chars. One big vector would let a huge description completely drown out a short abstract and the claims. Per-section chunking keeps each piece sharp.

---

## 5. Which fields to embed

**Decision:** Embed everything (abstract, claims, description), but tag each chunk with its section type.

Claims had to be in — they're the legally important part. Abstract is a clean summary. I wasn't sure about description at first, but instead of guessing, I embedded everything with tags so I could filter or reweight later without re-embedding.

It turned out the truncation issue (9.3% of chunks are too long for the model) almost entirely hits description paragraphs, while claims and abstracts fit fine. So "embed everything" was basically free to defend.

---

## 6. Missing data

**Decision:** Skip the missing section, never drop the whole patent.

18.6% of patents are missing `detailed_description`, but every patent has claims and abstract. Since claims are the most important field for novelty checking, dropping a patent because it's missing a description could hide a real prior-art match.

---

## 7. Embedding model

**Decision:** `all-MiniLM-L6-v2` — small, fast, 384 dimensions, runs on CPU.

Builds the whole index in ~52s and answers queries in ~40ms. The ~256-token limit means some long chunks get truncated, but for a Part 1 MVP over 640 patents, the speed and simplicity is worth that tradeoff.

---

## 8. Pre-filter vs. post-filter

**Decision:** Pre-filter — apply metadata filters *before* similarity math.

Two reasons:
- **Faster:** similarity only runs on surviving chunks
- **Correct:** post-filtering picks top-k first, then removes non-matching results, which can leave you with too few results or none. Pre-filtering draws top-k from the valid pool, so this can't happen.

Verified by checking that a patent's score stays the same whether or not filters are applied — the filter only gates eligibility, doesn't change ranking.

---

## 9. Things I deferred or changed my mind on

This is the honest part.

- **Deferred: which fields to embed.** I didn't lock this in until I could see where matches came from. The tag-everything approach meant deferring cost nothing.

- **Deferred: chunking granularity.** I waited for the length stats before committing to per-section chunking. The decision was based on measured field lengths, not assumptions.

- **Changed my mind: "description is noise."** I expected descriptions to be low-value boilerplate. The data said otherwise — description chunks won 14 of 15 top results in the demo. Turns out natural-language queries land on plain-prose descriptions way more than legal claim language, and descriptions have ~40× more chunks per patent so max-pooling gives them more chances to produce a high-scoring hit.

  This creates a real tension: the engine matches on descriptions ~93% of the time, but a novelty check ultimately cares about claims. I documented this as the top limitation with a proposed fix (section weighting) rather than hacking in a quick solution. Better to validate it properly with labeled relevance data in Part 3.

---

## 10. Scaling architecture — the funnel

**Decision:** Metadata pre-filter → quantized ANN over document-level vectors (in RAM) → cross-encoder re-rank on hydrated chunks for ~100 survivors.

The problem: 500M chunk vectors won't fit in RAM (~768 GB). But 10M document-level vectors quantized to int8 ≈ ~4 GB will. So we do chunk-level scoring only in Phase 2 on a small survivor set instead of across the whole corpus. This keeps Part 1's behavior (show the matching claim) while staying within a single machine's memory budget.

Tradeoffs I'm aware of: Phase 1 recall caps everything, cross-encoder is the cost driver, unfiltered queries need scatter-gather across shards, updating quantized HNSW indexes is awkward. All documented in the design doc with mitigations.

## 11. Which PoC to build

**Decision:** Postgres metadata store with indexed pre-filtering + a live status view.

Other options I considered:
- Status dashboard from dummy data — proves nothing real
- Full FAISS index — too much for a quick PoC
- Containerize Part 1 — just plumbing, no design substance

The Postgres store was the best fit because it directly fixes a Part 1 limitation (the Python-loop filter becomes a fast indexed DB query) and the status view shows real data instead of dummy counts. It makes a clean story: identified a limitation → designed the fix → built and proved it works.

`EXPLAIN ANALYZE` showed Postgres using a Bitmap Index Scan for `LIKE 'B60B%'`. At 640 rows it would normally prefer a sequential scan (correct for tiny tables), so I forced the index path to demonstrate it works. At millions of rows the optimizer picks the index automatically. The index needed `text_pattern_ops` to support prefix LIKE queries — a standard Postgres thing I had to handle.

---

## Summary

The decisions that shaped the system most: framing it as a *checker* not a builder, per-section chunking to protect claim signal, and pre-filtered hybrid search for speed and correctness. For scaling, the pre-filter became a Postgres indexed lookup, and search became a funnel that defers expensive chunk scoring to a small survivor set. I tried to defer decisions until I had data, and let measurements (field lengths, missing rates, truncation counts, match distribution, query plans) override my assumptions.
