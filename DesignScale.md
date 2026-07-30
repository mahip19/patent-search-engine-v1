# Scaling to 10 Million Patents

How the Part 1 engine would work at full patent corpus scale (~10M patents).

## The problem

Part 1 works because everything fits in memory and scanning 32K chunks takes ~40ms. That breaks at 10M patents. The chunk multiplier from our sample is ~50× (640 patents → 32,439 chunks), so **10M patents ≈ 500M chunks**.

Two things break:
- **Memory:** 500M vectors × 384 dims × 4 bytes = ~768 GB. Way too much for one machine.
- **Speed:** A linear scan that took 40ms over 32K chunks would take minutes over 500M.

Build time isn't the problem — patents come in weekly batches, so embedding is a background job that doesn't block search.

The fix is a **retrieval funnel** — throw away irrelevant stuff early and cheap, only spend expensive computation on what's left.

## Components

| Component | What it does | Tech |
|-----------|-------------|------|
| Ingestion workers | Parse new patents into chunks | Containerized Python behind a queue |
| Job queue | Decouple ingestion from indexing, handle retries | SQS / Celery / RabbitMQ |
| Embedding service | Turn text into vectors | `all-MiniLM-L6-v2` on GPU (batched) |
| Vector index (Phase 1) | Fast approximate retrieval | HNSW or IVF over **document-level** vectors, quantized, in RAM (Qdrant/Weaviate/FAISS) |
| Chunk store (Phase 2) | Raw chunk text for re-ranking | S3 + Postgres for lookup |
| Metadata store | Classification, title, abstract, status | Postgres with indexes |
| Re-ranker | Precise second-phase scoring | Cross-encoder on GPU |
| Query API | Orchestrates the funnel | Stateless service behind load balancer |
| Monitoring | Track health and index status | Prometheus + Grafana |

The key decision: **Phase 1 uses one compact vector per patent** (from abstract + main claims), **not** all 500M chunk vectors. Chunk-level scoring only happens in Phase 2 on ~100 survivors. This keeps the hot index small enough to fit in RAM.

## Pipelines

### Ingestion (offline, async)

1. Scheduled job picks up the weekly patent batch, queues one message per patent.
2. Workers parse each patent into chunks, same missing-field policy as Part 1.
3. Chunk text goes to chunk store, metadata goes to Postgres with `index_status = pending`.
4. Embedding service creates the document-level vector.
5. Vector gets added to the right shard of the ANN index. On success, status flips to `indexed`.
6. If anything fails, the message stays on the queue for retry. Patent stays `pending`/`failed`. Pipeline is idempotent.

### Query serving (online — the funnel)

User searches for *"a vehicle wheel that reduces vibration"* with a `B60B` filter:

1. **Encode query** — one 384-dim vector (fixed cost, doesn't depend on corpus size).
2. **Pre-filter** — classification constraint routes to only the B60B shard(s). Pool drops from ~10M to maybe a few hundred thousand before any similarity math.
3. **Phase 1 (coarse)** — quantized ANN index returns top ~100–500 patents by document-level similarity. Takes a few milliseconds.
4. **Fetch chunks** — pull the raw chunk text for those ~100 survivors from the chunk store.
5. **Phase 2 (precise)** — cross-encoder scores every (query, chunk) pair. This is the expensive step, but it only runs on hundreds of chunks, not millions.
6. **Return** — max-pool chunk scores per patent, sort, return top-k with the matching passage, just like Part 1.

## Cost estimate (rough)

All numbers are order-of-magnitude, just to show where money goes.

**One-time backfill (embedding 500M chunks):**
- ~7,500 chunks/s on GPU → ~18 GPU-hours → parallelize across 10 GPUs → done in ~2 hours. About **$30–50 total**. Embedding is cheap.

**Monthly storage:**
- ANN index in RAM: 10M × 384 × 4 bytes = ~15 GB float32, ~4 GB quantized. 2–3 replicas: **~$200–600/mo**
- Chunk text on S3: ~250 GB → **~$6/mo**
- Postgres: 10M rows → **~$50–200/mo**

**Monthly compute:**
- Incremental indexing: ~7K new patents/week → minutes of GPU → **negligible**
- Phase 1 serving (ANN): CPU-cheap → **~$100–300/mo**
- Phase 2 serving (cross-encoder): this is the big one, scales with QPS → **~$500–2,000/mo**

**Total:** low **thousands/month** at moderate traffic. Cross-encoder serving dominates. If cost is a problem, reduce how many candidates hit Phase 2.

## Error handling

- **Retryable ingestion.** Each patent is independent. Failures retry from the queue. Repeated failures go to a dead-letter queue and get marked `failed` in the DB. One bad patent never blocks the batch.
- **Missing fields.** Same as Part 1 — skip the missing section, keep the patent.
- **Indexing outage.** Search keeps working on the existing index, you just don't get new patents until indexing recovers. Freshness degrades, availability doesn't.
- **Shard failover.** Replicas mean losing a node hurts throughput, not correctness.
- **Re-ranker down.** API can fall back to Phase 1 results — less precise but still useful.

## Tracking what's indexed

- **Contents:** metadata store has one row per patent with `index_status` (pending/indexed/failed), model version, and timestamps. A simple query tells you how many are indexed, how many failed, and how fresh the data is. Also lets you re-index safely after a model upgrade.
- **Health:** Prometheus metrics — queue depth, dead-letter count, embedding throughput, ANN latency (p50/p95), cross-encoder latency, error rates. A status dashboard shows indexed-vs-pending counts and per-stage health.

## Challenges (honest)

1. **Phase 1 recall limits everything.** The re-ranker can only score what Phase 1 lets through. If we only index abstract + Claim 1, a patent whose 7th claim is the real match might never make the top 100. *Fix:* widen Phase 1 (retrieve more candidates, richer document vectors), accepting more Phase 2 cost.

2. **Cross-encoder cost.** Phase 2 is the cost and latency driver. Running it on hundreds of pairs per query needs GPUs. *Fix:* add a cheap mid-tier re-ranker between ANN and cross-encoder to cut candidates further.

3. **Unfiltered queries.** Sharding by classification is great when the user filters by B60B, but a query with no filter has to fan out across all shards and merge. *Fix:* scatter-gather with a merge step. Accept that unfiltered = expensive.

4. **Updating the ANN index.** HNSW graphs are awkward to update incrementally, especially when quantized and sharded. *Fix:* build a fresh shadow index in the background and hot-swap it.

5. **Stacked recall loss.** Quantization loses some recall, ANN loses some recall, together it compounds. *Fix:* hold out a labeled query set and monitor recall so degradation gets caught.

## Summary

The design is a funnel: **metadata pre-filtering** narrows by classification/title, **quantized ANN on document-level vectors** does cheap coarse retrieval that fits in RAM, and a **cross-encoder re-rank on hydrated chunks** gives precise results only on ~100 survivors. This keeps Part 1's chunk-level matching behavior at 10M-patent scale. The main cost is the cross-encoder, the main risk is Phase 1 recall. Both are called out with mitigations.
