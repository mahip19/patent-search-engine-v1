import random
import time

import numpy as np
from sentence_transformers import SentenceTransformer, CrossEncoder, InputExample, losses
from torch.utils.data import DataLoader

from patent_index import load_and_chunk

SEED = 42
BI_MODEL = "all-MiniLM-L6-v2"
CROSS_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
FINETUNE_DIR = "./finetuned_model"
DATA_DIR = "data/patent_data_small"
SEP = "=" * 70


def embed_index(model, chunks):
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, batch_size=64, show_progress_bar=True)
    embeddings = np.array(embeddings, dtype=np.float32)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    embeddings /= norms
    return embeddings


def evaluate_biencoder(model, eval_chunks, eval_embeddings, test_queries):
    chunk_pids = [c["patent_id"] for c in eval_chunks]

    query_texts = [abstract for _, abstract in test_queries]
    query_vecs = model.encode(query_texts, batch_size=64, show_progress_bar=False)
    query_vecs = np.array(query_vecs, dtype=np.float32)
    norms = np.linalg.norm(query_vecs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    query_vecs /= norms

    with np.errstate(all="ignore"):
        all_scores = query_vecs @ eval_embeddings.T
    all_scores = np.nan_to_num(all_scores, nan=0.0, posinf=0.0, neginf=0.0)

    recall_1 = 0
    recall_10 = 0
    mrr_sum = 0.0

    for i, (target_pid, _) in enumerate(test_queries):
        scores = all_scores[i]

        best_per_patent = {}
        for pid, score in zip(chunk_pids, scores):
            score_f = float(score)
            if pid not in best_per_patent or score_f > best_per_patent[pid]:
                best_per_patent[pid] = score_f

        ranked = sorted(best_per_patent.items(), key=lambda x: x[1], reverse=True)

        for r, (pid, _) in enumerate(ranked, 1):
            if pid == target_pid:
                if r <= 1:
                    recall_1 += 1
                if r <= 10:
                    recall_10 += 1
                mrr_sum += 1.0 / r
                break

    n = len(test_queries)
    return {"Recall@1": recall_1 / n, "Recall@10": recall_10 / n, "MRR": mrr_sum / n}


def evaluate_with_rerank(model, reranker, eval_chunks, eval_embeddings,
                         test_queries, rerank_candidates=50):
    chunk_pids = [c["patent_id"] for c in eval_chunks]

    query_texts = [abstract for _, abstract in test_queries]
    query_vecs = model.encode(query_texts, batch_size=64, show_progress_bar=False)
    query_vecs = np.array(query_vecs, dtype=np.float32)
    norms = np.linalg.norm(query_vecs, axis=1, keepdims=True)
    norms = np.maximum(norms, 1e-10)
    query_vecs /= norms

    with np.errstate(all="ignore"):
        all_scores = query_vecs @ eval_embeddings.T
    all_scores = np.nan_to_num(all_scores, nan=0.0, posinf=0.0, neginf=0.0)

    pid_to_chunks = {}
    for c in eval_chunks:
        pid_to_chunks.setdefault(c["patent_id"], []).append(c)

    recall_1 = 0
    recall_10 = 0
    mrr_sum = 0.0

    for i, (target_pid, query) in enumerate(test_queries):
        scores = all_scores[i]

        best_per_patent = {}
        for pid, score in zip(chunk_pids, scores):
            score_f = float(score)
            if pid not in best_per_patent or score_f > best_per_patent[pid]:
                best_per_patent[pid] = score_f

        ranked_p1 = sorted(best_per_patent.items(), key=lambda x: x[1], reverse=True)
        candidate_pids = [pid for pid, _ in ranked_p1[:rerank_candidates]]

        pairs = []
        pair_pids = []
        for pid in candidate_pids:
            patent_chunks = pid_to_chunks.get(pid, [])
            claims = [c for c in patent_chunks if c["section"] == "claim"][:5]
            descs = [c for c in patent_chunks if c["section"] == "description"][:1]
            selected = claims + descs
            if not selected:
                selected = patent_chunks[:6]
            for c in selected:
                pairs.append((query, c["text"]))
                pair_pids.append(pid)

        if not pairs:
            continue

        ce_scores = reranker.predict(pairs, batch_size=64, show_progress_bar=False)

        best_ce = {}
        for pid, score in zip(pair_pids, ce_scores):
            score_f = float(score)
            if pid not in best_ce or score_f > best_ce[pid]:
                best_ce[pid] = score_f

        ranked = sorted(best_ce.items(), key=lambda x: x[1], reverse=True)

        for r, (pid, _) in enumerate(ranked, 1):
            if pid == target_pid:
                if r <= 1:
                    recall_1 += 1
                if r <= 10:
                    recall_10 += 1
                mrr_sum += 1.0 / r
                break

    n = len(test_queries)
    return {"Recall@1": recall_1 / n, "Recall@10": recall_10 / n, "MRR": mrr_sum / n}


def main():
    chunks, patents_meta = load_and_chunk(DATA_DIR)

    # ── Train/test split ─────────────────────────────────────────────────
    all_pids = sorted(patents_meta.keys())
    rng = random.Random(SEED)
    shuffled = list(all_pids)
    rng.shuffle(shuffled)
    split_idx = int(len(shuffled) * 0.8)
    train_pids = set(shuffled[:split_idx])
    test_pids = set(shuffled[split_idx:])

    print(f"Train patents: {len(train_pids)}")
    print(f"Test patents:  {len(test_pids)}")

    # ── Eval index: claims + description only (no abstracts) ─────────────
    eval_chunks = [c for c in chunks if c["section"] != "abstract"]
    print(f"Eval index:    {len(eval_chunks)} chunks (abstracts excluded)")

    test_queries = [(pid, patents_meta[pid]["abstract"])
                    for pid in sorted(test_pids)]

    # ── (A) Baseline bi-encoder ──────────────────────────────────────────
    print(f"\n{SEP}")
    print("  (A) BASELINE BI-ENCODER — full test set")
    print(SEP)

    model = SentenceTransformer(BI_MODEL)
    print("Embedding eval index...")
    eval_embeddings = embed_index(model, eval_chunks)

    t0 = time.time()
    metrics_a = evaluate_biencoder(model, eval_chunks, eval_embeddings, test_queries)
    time_a = time.time() - t0

    for k, v in metrics_a.items():
        print(f"  {k}:  {v:.3f}")
    print(f"  Time: {time_a:.1f}s ({len(test_queries)} queries)")

    # ── (B) Baseline + cross-encoder rerank (30-query subset) ────────────
    print(f"\n{SEP}")
    print("  (B) BASELINE + CROSS-ENCODER RERANK — 30-query subset")
    print(SEP)

    reranker = CrossEncoder(CROSS_MODEL)
    subset_queries = test_queries[:30]

    t0 = time.time()
    metrics_b = evaluate_with_rerank(
        model, reranker, eval_chunks, eval_embeddings, subset_queries)
    time_b = time.time() - t0

    for k, v in metrics_b.items():
        print(f"  {k}:  {v:.3f}")
    print(f"  Time: {time_b:.1f}s ({len(subset_queries)} queries)")

    # ── Fine-tune on train patents ───────────────────────────────────────
    print(f"\n{SEP}")
    print("  FINE-TUNING on train patent (abstract, claim) pairs")
    print(SEP)

    claims_by_patent = {}
    for c in chunks:
        if c["patent_id"] in train_pids and c["section"] == "claim":
            claims_by_patent.setdefault(c["patent_id"], []).append(c["text"])

    train_pairs = []
    for pid, claim_texts in claims_by_patent.items():
        abstract = patents_meta[pid]["abstract"]
        for claim in claim_texts[:8]:
            train_pairs.append(InputExample(texts=[abstract, claim]))

    print(f"  Training pairs: {len(train_pairs)} "
          f"(from {len(claims_by_patent)} patents, up to 8 claims each)")

    ft_model = SentenceTransformer(BI_MODEL)
    train_dataloader = DataLoader(train_pairs, shuffle=True, batch_size=16)
    train_loss = losses.MultipleNegativesRankingLoss(ft_model)

    t0 = time.time()
    ft_model.fit(
        train_objectives=[(train_dataloader, train_loss)],
        epochs=1,
        show_progress_bar=True,
    )
    ft_time = time.time() - t0
    ft_model.save(FINETUNE_DIR)
    print(f"  Fine-tune time: {ft_time:.1f}s")
    print(f"  Saved to: {FINETUNE_DIR}")

    # ── (C) Fine-tuned bi-encoder ────────────────────────────────────────
    print(f"\n{SEP}")
    print("  (C) FINE-TUNED BI-ENCODER — full test set")
    print(SEP)

    ft_model = SentenceTransformer(FINETUNE_DIR)
    print("Re-embedding eval index with fine-tuned model...")
    ft_embeddings = embed_index(ft_model, eval_chunks)

    t0 = time.time()
    metrics_c = evaluate_biencoder(ft_model, eval_chunks, ft_embeddings, test_queries)
    time_c = time.time() - t0

    for k, v in metrics_c.items():
        print(f"  {k}:  {v:.3f}")
    print(f"  Time: {time_c:.1f}s ({len(test_queries)} queries)")

    # ── Comparison table ─────────────────────────────────────────────────
    print(f"\n{SEP}")
    print("  COMPARISON TABLE")
    print(SEP)
    print(f"  {'metric':<12s}  {'baseline':>10s}  {'+rerank(30)':>12s}  {'finetuned':>10s}")
    print(f"  {'─'*12}  {'─'*10}  {'─'*12}  {'─'*10}")
    for metric in ["Recall@1", "Recall@10", "MRR"]:
        a = metrics_a[metric]
        b = metrics_b[metric]
        c = metrics_c[metric]
        print(f"  {metric:<12s}  {a:>10.3f}  {b:>12.3f}  {c:>10.3f}")
    print(f"\n  Note: +rerank column evaluated on {len(subset_queries)}-query "
          f"subset; others on full {len(test_queries)}-query test set.")
    print(SEP)


if __name__ == "__main__":
    main()
