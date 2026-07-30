# Scaling Design: Patent Search at 10 Million Patents

This document describes how the Part 1 search engine would be implemented at the
scale of the full patent corpus (~10M patents). It is written to be implementable
by an intern: it names concrete components, describes the data flow, estimates
cost, and — as the task explicitly invites — acknowledges where the simple design
breaks and what we would do about it.

## 1. The core problem at scale

Part 1 works because everything fits in memory and a brute-force cosine over 32K
chunks takes ~40 ms. Neither holds at 10M patents. The measured chunk multiplier
from the sample is ~50× (640 patents → 32,439 chunks), so **10M patents ≈ 500M
chunks.** Two things break:

- **Memory / index size.** 500M chunk vectors at 384 dims × 4 bytes ≈ **768 GB** of
  raw float32 — far past a single machine's RAM, and brute-force search over it
  per query is hopeless.
- **Search latency.** A linear scan that was 40 ms over 32K chunks becomes minutes
  over 500M.

Build/embedding time is _not_ the binding constraint: patents publish in weekly
batches, so indexing is an asynchronous background job that never blocks the live
query path.

The design is therefore a **retrieval funnel** — strip away irrelevant candidates
as cheaply as possible early, and spend expensive computation only on the handful
that survive.

## 2. System components

| Component                  | Role                                                       | Concrete choice                                                                                                                     |
| -------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **Ingestion workers**      | Pull new patents, parse XML/JSON into chunks               | Containerized Python workers behind a queue                                                                                         |
| **Job queue**              | Decouple ingestion from indexing; retryable units of work  | SQS / Celery / RabbitMQ                                                                                                             |
| **Embedding service**      | Turn chunk text into vectors                               | `all-MiniLM-L6-v2` on GPU inference nodes (batched)                                                                                 |
| **Vector index (Phase-1)** | Fast approximate coarse retrieval                          | ANN index (HNSW or IVF) over **document-level** vectors, **quantized**, held in RAM; managed vector DB (Qdrant / Weaviate) or FAISS |
| **Chunk store (Phase-2)**  | Raw chunk text for precise re-ranking                      | Object store (S3) + NoSQL/Postgres for lookup by patent_id                                                                          |
| **Metadata store**         | Classification, title, abstract, filing date, index status | Postgres (indexed on classification prefix, title)                                                                                  |
| **Re-ranker**              | Precise second-phase scoring                               | Cross-encoder on GPU inference nodes                                                                                                |
| **Query API / router**     | Orchestrates the funnel, applies filters, routes to shards | Stateless service behind a load balancer                                                                                            |
| **Monitoring / status**    | Track what's indexed and whether the system is healthy     | Prometheus + Grafana; a status table in Postgres                                                                                    |

Key architectural decision carried from Part 1: **Phase 1 uses one compact
document-level vector per patent** (e.g. abstract + representative claims),
**not** the 500M chunk vectors. Chunk-level precision is expensive and is deferred
to Phase 2, where it runs only on ~100 survivors. This is what keeps the hot index
small enough to live in RAM.

## 3. Major pipelines

### 3.1 Ingestion & indexing pipeline (asynchronous, offline)

1. A scheduled job detects the new weekly patent batch and enqueues one message
   per patent (or per file).
2. Ingestion workers pull messages, parse each patent into chunks (abstract,
   per-claim, per-description-paragraph), applying the Part 1 missing-field policy
   (skip a missing section, never drop the patent).
3. Chunk text is written to the **chunk store**; patent metadata is written to the
   **metadata store** with `index_status = pending`.
4. The embedding service embeds the document-level vector for Phase 1 (and chunk
   vectors if we choose to pre-embed rather than re-embed at re-rank time).
5. The document-level vector is upserted into the correct **shard** of the ANN
   index (see sharding under Challenges). On success, metadata `index_status` is
   set to `indexed`.
6. Failures at any step leave the message on the queue for retry and the patent in
   `pending`/`failed` — so the pipeline is idempotent and self-healing.

### 3.2 Query-serving pipeline (online — the funnel)

A user submits _"a vehicle wheel that reduces vibration"_ with a `B60B` filter:

1. **Encode.** The query is embedded once into a 384-dim vector (fixed per-query
   cost, independent of corpus size).
2. **Pre-filter / route (metadata store + sharding).** The classification
   constraint routes the request only to the shard(s) holding B60B patents; the
   other classes are never touched. Candidate pool drops from ~10M to a few
   hundred thousand before any similarity math runs.
3. **Phase 1 — coarse ANN retrieval.** Inside the shard, the quantized ANN index
   returns the top ~100–500 candidate patents by document-level similarity in a
   few milliseconds, without scanning every vector.
4. **Hydrate (chunk store).** For those ~100 survivors, fetch their raw chunk text
   (claims + description paragraphs) from the chunk store. Heavy chunk data is
   pulled for hundreds of patents, never for millions.
5. **Phase 2 — precise re-rank (cross-encoder).** The query is paired with each
   survivor's chunks and scored by a cross-encoder, which judges the actual
   query↔passage relationship rather than a precomputed vector distance.
6. **Aggregate & return.** Max-pool the chunk scores to one score per patent, sort,
   and return the top-k as JSON — including the specific matching claim/paragraph,
   exactly as in Part 1.

This gives the best of both: a cheap, high-recall net over the whole (filtered)
corpus, and expensive high-precision scoring only where it matters.

## 4. Cost breakdown (order-of-magnitude)

Assumptions: 10M patents, ~500M chunks, `all-MiniLM-L6-v2` (384-dim), managed
cloud. Numbers are deliberately rough — the goal is to show where the money goes.

**One-time backfill (embedding 500M chunks):**

- At an observed ~650 chunks/s on a laptop CPU, GPU throughput of ~7,500 chunks/s
  is conservative → ~500M / 7,500 ≈ 18 GPU-hours on one GPU; parallelized across
  ~10 GPUs, done in ~2 hours. At ~$1.5/GPU-hr this is **~$30–50 total**. Embedding
  is cheap; it is a one-off.

**Ongoing storage (monthly):**

- **Phase-1 ANN index in RAM:** document-level = 10M × 384 × 4 B ≈ **15 GB**
  float32; scalar-quantized to int8 ≈ **3.8 GB**, plus HNSW graph overhead ≈ a few
  GB → fits on a single large memory instance. Run 2–3 replicas for throughput and
  failover: **~$200–600/mo**.
- **Chunk text store (S3):** ~500M chunks × ~500 B ≈ **250 GB** → **~$6/mo**.
- **Metadata store (managed Postgres):** 10M small rows → **~$50–200/mo**.

**Ongoing compute (monthly):**

- **Incremental indexing:** ~7,000 new patents/week × ~50 chunks ≈ 350K chunks/wk
  → minutes of GPU/week → **negligible**.
- **Query serving — Phase 1** (ANN + filter): CPU-cheap, scales to high QPS on a
  few API nodes → **~$100–300/mo**.
- **Query serving — Phase 2** (cross-encoder GPU): the real driver. A cross-encoder
  runs a full forward pass per (query, chunk) pair with no precomputation, so cost
  scales with QPS × chunks-per-query. Sized to load with autoscaling GPU nodes →
  **~$500–2,000/mo** depending on traffic.

**Rough total:** low **thousands of dollars/month** at moderate traffic, dominated
by cross-encoder serving. The clear lever if cost is a problem: reduce Phase-2 work
(fewer candidates, or a cheaper mid-tier re-ranker before the cross-encoder).

## 5. Error handling

- **Idempotent, retryable ingestion.** Each patent is an independent queue message;
  a failed parse/embed/upsert stays queued and retries. Repeated failures go to a
  **dead-letter queue** and mark the patent `failed` in metadata for inspection —
  one bad patent never blocks the batch.
- **Partial-patent tolerance.** The Part 1 missing-field policy carries over: a
  patent missing a section is still indexed on its remaining sections rather than
  rejected.
- **Index/serving decoupling.** Because indexing is offline, an indexing outage
  degrades _freshness_ (new patents show up late), not _availability_ (queries keep
  working against the existing index).
- **Shard failover.** ANN index replicas mean a lost node degrades throughput, not
  correctness.
- **Graceful query degradation.** If the Phase-2 re-ranker is unavailable, the API
  can fall back to returning Phase-1 (ANN) results — lower precision, still useful —
  rather than erroring.

## 6. Tracking contents & status

The task specifically asks how we track what's in the system and whether it's
healthy. Two layers:

- **Contents (what's indexed):** the metadata store holds one row per patent with
  `index_status` (`pending` / `indexed` / `failed`), embedding model version, and
  timestamps. A simple query answers "how many patents are indexed, how many
  pending, how many failed, and what's the freshness lag." This also enables safe
  re-indexing after a model upgrade (bump the version, re-embed in the background,
  swap).
- **Health (is it working):** standard metrics via Prometheus/Grafana — queue depth
  and dead-letter count (ingestion health), embedding throughput, ANN query
  latency (p50/p95), cross-encoder latency, and error rates per stage. A small
  **status dashboard** surfaces indexed-vs-pending counts and per-stage health at a
  glance. (This dashboard is the natural proof-of-concept piece — see PoC.)

## 7. Major challenges at scale (and honest tradeoffs)

These are the places the simple design strains. Naming them is the point.

1. **Phase-1 recall caps everything downstream.** The precise re-ranker can only
   re-rank what the coarse phase let through. If Phase 1 indexes only a document-
   level summary (abstract + Claim 1), a patent whose _seventh_ claim is the real
   collision may never enter the top 100, so the cross-encoder never sees it.
   _Mitigation:_ widen the Phase-1 net (retrieve more candidates; or index a richer
   document-level representation), accepting more Phase-2 cost for higher recall —
   and measure recall to tune the tradeoff.

2. **Cross-encoder serving cost & latency.** Phase 2 is the cost and latency
   driver. Running it on ~hundreds of pairs per query needs GPUs and can move
   latency out of the millisecond range. _Mitigation:_ a cheap mid-tier re-ranker
   (bi-encoder / smaller model) between ANN and cross-encoder to cut the candidate
   set further before the expensive model runs.

3. **Filter routing when there is no filter (cross-shard aggregation).** Sharding
   by classification is free when the user filters by B60B, but a query with _no_
   classification filter, or one spanning classes (e.g. a tire _sensor_ that is
   both mechanical and electronics), must fan out across shards and merge results.
   _Mitigation:_ scatter-gather across shards with a merge step, at higher cost;
   accept that unfiltered queries are the expensive case.

4. **Updating a quantized, sharded ANN index.** HNSW graphs are awkward to update
   incrementally, and the index is both quantized and sharded, so the "easy weekly
   background job" is really: insert into the right shard, occasionally rebuild.
   _Mitigation:_ build a fresh shadow index in the background and hot-swap it, so
   updates never disrupt live queries.

5. **Recall compounding.** Quantization costs some recall and ANN costs some
   recall; stacking both compounds the loss. _Mitigation:_ hold out a labeled
   query set and monitor recall so degradation is caught rather than silently
   shipped (this connects to the Part 3 evaluation work).

## 8. Summary

The design is a funnel: **metadata pre-filtering** shrinks the candidate pool using
constraints we already support, **quantized ANN over document-level vectors** gives
cheap high-recall coarse retrieval that fits in RAM, and a **cross-encoder re-rank
over hydrated chunks** gives precise scoring only on the ~100 survivors — preserving
the chunk-level, show-the-matching-claim behavior of Part 1 at 10M-patent scale.
The dominant cost is cross-encoder serving; the dominant risk is Phase-1 recall.
Neither is hidden — both are called out with mitigations, per the task's guidance
to pick something simple and acknowledge its challenges.
