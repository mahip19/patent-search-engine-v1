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

    all_results = []

    # ── 1. Semantic search beats keyword matching ────────────────────────
    # The top hit's title shares no words with the query, demonstrating
    # that semantic (meaning-based) matching beats keyword matching.
    all_results += run_search(
        engine,
        "1) PURE SEMANTIC — top hit shares no words with query, "
        "demonstrating semantic (meaning-based) matching beats keyword matching",
        "bicycle wheel spoke that reduces vibration",
    )

    # ── 2. Same query + classification filter ────────────────────────────
    # Restrict to B60C (tire/tyre patents). Pool shrinks, search speeds up.
    all_results += run_search(
        engine,
        "2) SAME QUERY + classification filter (B60C = tires)",
        "bicycle wheel spoke that reduces vibration",
        classification_prefix="B60C",
    )

    # ── 3. Hybrid: two filters stacked ───────────────────────────────────
    all_results += run_search(
        engine,
        "3) HYBRID — classification=B60B + title_contains=\"wheel\"",
        "aerodynamic drag reduction at high speed",
        classification_prefix="B60B",
        title_contains="wheel",
    )

    # ── 4. Empty result: filters eliminate everything ────────────────────
    all_results += run_search(
        engine,
        "4) EMPTY RESULT — impossible filter combination",
        "anything",
        classification_prefix="ZZZZ",
        title_contains="nonexistent",
    )

    # ── Summary tally ────────────────────────────────────────────────────
    section_counts = {}
    for r in all_results:
        s = r["best_section"]
        section_counts[s] = section_counts.get(s, 0) + 1

    print(f"\n{SEP}")
    print("  Section match distribution across demo results:")
    for section in ["abstract", "claim", "description"]:
        print(f"    {section}: {section_counts.get(section, 0)}")
    print(SEP)


if __name__ == "__main__":
    main()
