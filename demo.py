import time
from patent_index import PatentSearchEngine, print_results

DATA_DIR = "data/patent_data_small"
SEP = "=" * 70


def run_search(engine, label, query, top_k=5, **filters):
    print(f"\n{SEP}")
    print(f"  {label}")
    print(f"  Query: \"{query}\"")
    if filters:
        print(f"  Filters: {filters}")
    print(SEP)

    t0 = time.time()
    results, surviving, total = engine.search(query, top_k=top_k, **filters)
    elapsed = time.time() - t0

    print(f"  Chunks: {total} -> {surviving} after filtering")

    if results:
        print_results(results)
    else:
        print("\n  No results found — filters eliminated all patents.")

    print(f"  Search time: {elapsed*1000:.1f}ms")
    return results


def main():
    print("Building index (one-time cost)...\n")
    t0 = time.time()
    engine = PatentSearchEngine(DATA_DIR)
    print(f"Index built in {time.time() - t0:.1f}s")

    # ── 1. Semantic search beats keyword matching ────────────────────────
    # "quieter ride on rough pavement" shares zero words with the top hit's
    # title, but the model understands the concept maps to tire noise
    # reduction and sound-absorbing structures.
    run_search(
        engine,
        "1) PURE SEMANTIC — no keywords in common with top hits",
        "quieter ride on rough pavement",
    )

    # ── 2. Same query + classification filter ────────────────────────────
    # Restrict to B60C (tire/tyre patents). Pool shrinks, search speeds up.
    run_search(
        engine,
        "2) SAME QUERY + classification filter (B60C = tires)",
        "quieter ride on rough pavement",
        classification_prefix="B60C",
    )

    # ── 3. Hybrid: two filters stacked ───────────────────────────────────
    run_search(
        engine,
        "3) HYBRID — classification=B60B + title_contains=\"wheel\"",
        "aerodynamic drag reduction at high speed",
        classification_prefix="B60B",
        title_contains="wheel",
    )

    # ── 4. Empty result: filters eliminate everything ────────────────────
    run_search(
        engine,
        "4) EMPTY RESULT — impossible filter combination",
        "anything",
        classification_prefix="ZZZZ",
        title_contains="nonexistent",
    )


if __name__ == "__main__":
    main()
