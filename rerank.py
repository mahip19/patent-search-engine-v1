import time

from sentence_transformers import CrossEncoder
from patent_index import PatentSearchEngine, print_results

RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
MAX_CHUNKS_PER_PATENT = 6


def two_phase_search(engine, query, top_k=10, rerank_candidates=50, **filters):
    # ── Phase 1: bi-encoder recall ───────────────────────────────────────
    t0 = time.time()
    phase1_results, surviving, total = engine.search(
        query, top_k=rerank_candidates, **filters)
    phase1_time = time.time() - t0

    if not phase1_results:
        return [], phase1_time, 0.0

    # ── Gather high-value chunks per candidate patent ────────────────────
    candidate_pids = {r["patent_id"] for r in phase1_results}

    # build a quick lookup: patent_id -> list of (section, text) for
    # abstract + claim chunks
    pid_extra_chunks = {}
    for chunk in engine.chunks:
        pid = chunk["patent_id"]
        if pid not in candidate_pids:
            continue
        if chunk["section"] in ("abstract", "claim"):
            pid_extra_chunks.setdefault(pid, []).append(
                (chunk["section"], chunk["text"]))

    # for each candidate, collect chunks to send to the cross-encoder:
    # abstract (1) + up to 5 claims, falling back to phase-1 best chunk
    candidate_data = []
    for r in phase1_results:
        pid = r["patent_id"]
        chunks_to_score = []

        extras = pid_extra_chunks.get(pid, [])
        abstracts = [(s, t) for s, t in extras if s == "abstract"]
        claims = [(s, t) for s, t in extras if s == "claim"]

        for s, t in abstracts[:1]:
            chunks_to_score.append((s, t))
        for s, t in claims[:5]:
            chunks_to_score.append((s, t))

        # always include the phase-1 winning chunk if not already present
        best_text = r["best_chunk_text"]
        if not any(t == best_text for _, t in chunks_to_score):
            chunks_to_score.append((r["best_section"], best_text))

        candidate_data.append({
            "patent_id": pid,
            "title": r["title"],
            "classification": r["classification"],
            "phase1_score": r["score"],
            "chunks_to_score": chunks_to_score,
        })

    # ── Phase 2: cross-encoder precision ─────────────────────────────────
    reranker = CrossEncoder(RERANK_MODEL)

    # build one flat batch of (query, chunk) pairs
    pairs = []
    pair_map = []  # (candidate_index, chunk_index_within_candidate)
    for ci, cand in enumerate(candidate_data):
        for chi, (section, text) in enumerate(cand["chunks_to_score"]):
            pairs.append((query, text))
            pair_map.append((ci, chi))

    t0 = time.time()
    all_scores = reranker.predict(pairs, batch_size=64, show_progress_bar=False)
    phase2_time = time.time() - t0

    # max-pool cross-encoder scores per candidate
    for ci, cand in enumerate(candidate_data):
        cand["rerank_score"] = float("-inf")

    for (ci, chi), score in zip(pair_map, all_scores):
        cand = candidate_data[ci]
        score_f = float(score)
        if score_f > cand["rerank_score"]:
            cand["rerank_score"] = score_f
            section, text = cand["chunks_to_score"][chi]
            cand["best_section"] = section
            cand["best_chunk_text"] = text

    # sort by cross-encoder score, return top_k
    candidate_data.sort(key=lambda c: c["rerank_score"], reverse=True)

    results = []
    for cand in candidate_data[:top_k]:
        results.append({
            "patent_id": cand["patent_id"],
            "title": cand["title"],
            "classification": cand["classification"],
            "phase1_score": cand["phase1_score"],
            "rerank_score": cand["rerank_score"],
            "best_section": cand["best_section"],
            "best_chunk_text": cand["best_chunk_text"],
        })

    return results, phase1_time, phase2_time


def print_reranked(results, top_n=None):
    for rank, r in enumerate(results[:top_n], 1):
        snippet = r["best_chunk_text"][:200]
        if len(r["best_chunk_text"]) > 200:
            snippet += "..."
        print(f"\n{'─'*70}")
        print(f"  #{rank}  bi={r['phase1_score']:.3f}  "
              f"cross={r['rerank_score']:.3f}  [{r['best_section']}]")
        print(f"  Patent {r['patent_id']}  |  {r['classification']}")
        print(f"  {r['title']}")
        print(f"  {snippet}")
    print(f"\n{'─'*70}")


def section_tally(results, top_n=5):
    counts = {}
    for r in results[:top_n]:
        s = r["best_section"]
        counts[s] = counts.get(s, 0) + 1
    return counts


if __name__ == "__main__":
    data_dir = "data/patent_data_small"
    query = "a bicycle wheel spoke that reduces vibration"

    print("Building index...\n")
    engine = PatentSearchEngine(data_dir)

    SEP = "=" * 70

    # ── Part 1 only (bi-encoder) ─────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  PHASE 1 ONLY (bi-encoder) — top 5")
    print(f"  Query: \"{query}\"")
    print(SEP)

    t0 = time.time()
    phase1_results, _, _ = engine.search(query, top_k=5)
    p1_time = time.time() - t0

    print_results(phase1_results)
    print(f"  Phase 1 time: {p1_time*1000:.1f}ms")

    # ── Two-phase (re-ranked) ────────────────────────────────────────────
    print(f"\n{SEP}")
    print(f"  TWO-PHASE (bi-encoder → cross-encoder re-rank) — top 5")
    print(f"  Query: \"{query}\"")
    print(SEP)

    reranked, p1_time_2, p2_time = two_phase_search(
        engine, query, top_k=5, rerank_candidates=50)

    print_reranked(reranked)
    print(f"  Phase 1 time: {p1_time_2*1000:.1f}ms")
    print(f"  Phase 2 time: {p2_time*1000:.1f}ms")

    # ── Before/after section tally ───────────────────────────────────────
    before = section_tally(phase1_results)
    after = section_tally(reranked)

    print(f"\n{SEP}")
    print(f"  SECTION TALLY (top 5): before vs. after re-ranking")
    print(SEP)
    for section in ["abstract", "claim", "description"]:
        b = before.get(section, 0)
        a = after.get(section, 0)
        print(f"  {section:15s}  before={b}  after={a}")
    print(f"\n{SEP}")
