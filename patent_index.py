import json
import glob
import time

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
TRUNCATION_CHAR_THRESHOLD = 1000


def load_and_chunk(data_dir):
    files = sorted(glob.glob(f"{data_dir}/patents_ipa*.json"))
    if not files:
        raise FileNotFoundError(f"No patents_ipa*.json files found in {data_dir}")

    chunks = []
    patents_meta = {}

    for path in files:
        with open(path) as f:
            patents = json.load(f)

        for patent in patents:
            pid = patent["doc_number"]
            title = patent["title"]
            classification = patent["classification"]
            abstract = patent["abstract"]

            patents_meta[pid] = {
                "title": title,
                "classification": classification,
                "abstract": abstract,
            }

            if abstract and abstract.strip():
                chunks.append({
                    "patent_id": pid,
                    "title": title,
                    "classification": classification,
                    "section": "abstract",
                    "chunk_index": 0,
                    "text": abstract.strip(),
                })

            for i, claim_text in enumerate(patent.get("claims", [])):
                if claim_text and claim_text.strip():
                    chunks.append({
                        "patent_id": pid,
                        "title": title,
                        "classification": classification,
                        "section": "claim",
                        "chunk_index": i,
                        "text": claim_text.strip(),
                    })

            for i, para_text in enumerate(patent.get("detailed_description", [])):
                if para_text and para_text.strip():
                    chunks.append({
                        "patent_id": pid,
                        "title": title,
                        "classification": classification,
                        "section": "description",
                        "chunk_index": i,
                        "text": para_text.strip(),
                    })

    return chunks, patents_meta


class PatentSearchEngine:
    def __init__(self, data_dir):
        print("Loading and chunking patents...")
        self.chunks, self.patents_meta = load_and_chunk(data_dir)

        print(f"  {len(self.patents_meta)} patents, {len(self.chunks)} chunks")

        print("Loading model and embedding chunks...")
        self.model = SentenceTransformer(MODEL_NAME)

        texts = [c["text"] for c in self.chunks]
        long_count = sum(1 for t in texts if len(t) > TRUNCATION_CHAR_THRESHOLD)
        if long_count:
            print(f"  WARNING: {long_count}/{len(texts)} chunks exceed ~256 tokens "
                  f"(>{TRUNCATION_CHAR_THRESHOLD} chars) and will be truncated")

        self.embeddings = self.model.encode(
            texts, batch_size=64, show_progress_bar=True,
        )
        self.embeddings = np.array(self.embeddings, dtype=np.float32)

        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        zero_mask = (norms < 1e-10).flatten()
        if zero_mask.any():
            print(f"  NOTE: {zero_mask.sum()} chunks have zero-norm embeddings (empty text); "
                  "they will not match any query")
        norms = np.maximum(norms, 1e-10)
        self.embeddings /= norms
        self.embeddings[zero_mask] = 0.0

        # pre-compute arrays for fast filtering and max-pooling
        self._chunk_patent_ids = np.array([c["patent_id"] for c in self.chunks])
        self._chunk_classifications = np.array(
            [c["classification"].lower() for c in self.chunks])
        self._chunk_titles = np.array(
            [c["title"].lower() for c in self.chunks])
        self._chunk_abstracts = np.array(
            [self.patents_meta[c["patent_id"]]["abstract"].lower()
             for c in self.chunks])

        print("Index ready.\n")

    def search(self, query, top_k=10, classification_prefix=None,
               title_contains=None, abstract_contains=None):
        mask = self._build_filter_mask(
            classification_prefix, title_contains, abstract_contains)

        surviving = int(mask.sum())
        total = len(self.chunks)
        if surviving == 0:
            return []

        query_vec = self.model.encode([query])
        query_vec = np.array(query_vec, dtype=np.float32)
        query_vec /= np.linalg.norm(query_vec)

        filtered_embeddings = self.embeddings[mask]
        with np.errstate(all="ignore"):
            scores = (query_vec @ filtered_embeddings.T).flatten()
        scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)

        filtered_indices = np.where(mask)[0]
        filtered_pids = self._chunk_patent_ids[mask]

        # max-pool to patent level
        best_per_patent = {}
        for orig_idx, pid, score in zip(
                filtered_indices, filtered_pids, scores):
            if pid not in best_per_patent or score > best_per_patent[pid][1]:
                best_per_patent[pid] = (int(orig_idx), float(score))

        ranked = sorted(best_per_patent.items(), key=lambda x: x[1][1], reverse=True)

        results = []
        for pid, (chunk_idx, score) in ranked[:top_k]:
            chunk = self.chunks[chunk_idx]
            results.append({
                "patent_id": pid,
                "title": chunk["title"],
                "classification": chunk["classification"],
                "score": score,
                "best_section": chunk["section"],
                "best_chunk_text": chunk["text"],
            })

        return results, surviving, total

    def _build_filter_mask(self, classification_prefix, title_contains,
                           abstract_contains):
        mask = np.ones(len(self.chunks), dtype=bool)

        if classification_prefix is not None:
            prefix = classification_prefix.lower()
            mask &= np.array([c.startswith(prefix)
                              for c in self._chunk_classifications])

        if title_contains is not None:
            sub = title_contains.lower()
            mask &= np.array([sub in t for t in self._chunk_titles])

        if abstract_contains is not None:
            sub = abstract_contains.lower()
            mask &= np.array([sub in a for a in self._chunk_abstracts])

        return mask


def print_results(results, top_n=None):
    for rank, r in enumerate(results[:top_n], 1):
        snippet = r["best_chunk_text"][:200]
        if len(r["best_chunk_text"]) > 200:
            snippet += "..."
        print(f"\n{'─'*70}")
        print(f"  #{rank}  score={r['score']:.3f}  [{r['best_section']}]")
        print(f"  Patent {r['patent_id']}  |  {r['classification']}")
        print(f"  {r['title']}")
        print(f"  {snippet}")
    print(f"\n{'─'*70}")


if __name__ == "__main__":
    data_dir = "data/patent_data_small"

    t0 = time.time()
    engine = PatentSearchEngine(data_dir)
    build_time = time.time() - t0
    print(f"Index build time: {build_time:.1f}s")

    query = "a bicycle wheel spoke that reduces vibration"

    # (a) Pure semantic — no filters
    print(f"\n{'='*70}")
    print(f'(a) PURE SEMANTIC: "{query}"')
    print(f"{'='*70}")
    t0 = time.time()
    results, surviving, total = engine.search(query, top_k=10)
    elapsed = time.time() - t0
    print(f"Filter: {total} -> {surviving} chunks")
    print_results(results, top_n=3)
    print(f"Search time: {elapsed*1000:.1f}ms")

    # (b) classification_prefix="B60B"
    print(f"\n{'='*70}")
    print(f'(b) + classification_prefix="B60B"')
    print(f"{'='*70}")
    t0 = time.time()
    results, surviving, total = engine.search(
        query, top_k=10, classification_prefix="B60B")
    elapsed = time.time() - t0
    print(f"Filter: {total} -> {surviving} chunks")
    print_results(results, top_n=3)
    print(f"Search time: {elapsed*1000:.1f}ms")

    # (c) classification_prefix="B60B" AND title_contains="spoke"
    print(f"\n{'='*70}")
    print(f'(c) + classification_prefix="B60B" AND title_contains="spoke"')
    print(f"{'='*70}")
    t0 = time.time()
    results, surviving, total = engine.search(
        query, top_k=10, classification_prefix="B60B",
        title_contains="spoke")
    elapsed = time.time() - t0
    print(f"Filter: {total} -> {surviving} chunks")
    print_results(results, top_n=3)
    print(f"Search time: {elapsed*1000:.1f}ms")
