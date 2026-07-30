import glob
import json
import os
import sys
import time

import psycopg2
from psycopg2.extras import execute_values

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://localhost/patents")
DATA_DIR = "data/patent_data_small"


def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = True
        return conn
    except psycopg2.OperationalError as e:
        print(f"ERROR: Cannot connect to Postgres at {DATABASE_URL}")
        print(f"  {e}")
        print("Set DATABASE_URL or start Postgres and create the database:")
        print("  createdb patents")
        sys.exit(1)


# ── 1. Schema ────────────────────────────────────────────────────────────

def create_schema(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patents (
                patent_id       TEXT PRIMARY KEY,
                title           TEXT NOT NULL,
                classification  TEXT NOT NULL,
                abstract        TEXT NOT NULL,
                index_status    TEXT NOT NULL DEFAULT 'indexed',
                indexed_at      TIMESTAMP NOT NULL DEFAULT now()
            );
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_classification
            ON patents (classification text_pattern_ops);
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_patents_title_lower
            ON patents (lower(title) text_pattern_ops);
        """)
    print("Schema ready.")


# ── 2. Load ──────────────────────────────────────────────────────────────

def load_patents(conn, data_dir):
    files = sorted(glob.glob(f"{data_dir}/patents_ipa*.json"))
    if not files:
        print(f"No patents_ipa*.json files in {data_dir}")
        return

    rows = []
    for path in files:
        with open(path) as f:
            patents = json.load(f)
        for p in patents:
            rows.append((
                p["doc_number"],
                p["title"],
                p["classification"],
                p["abstract"],
            ))

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO patents (patent_id, title, classification, abstract)
            VALUES %s
            ON CONFLICT (patent_id) DO NOTHING
            """,
            rows,
            page_size=500,
        )

    with conn.cursor() as cur:
        cur.execute("ANALYZE patents")
        cur.execute("SELECT count(*) FROM patents")
        total = cur.fetchone()[0]

    print(f"Loaded {len(rows)} patents from {len(files)} files "
          f"({total} total rows in table).")


# ── 3. Pre-filter query ─────────────────────────────────────────────────

def filter_patents(conn, classification_prefix=None, title_contains=None,
                   abstract_contains=None):
    conditions = []
    params = []

    if classification_prefix is not None:
        conditions.append("classification LIKE %s")
        params.append(classification_prefix + "%")

    if title_contains is not None:
        conditions.append("lower(title) LIKE %s")
        params.append("%" + title_contains.lower() + "%")

    if abstract_contains is not None:
        conditions.append("lower(abstract) LIKE %s")
        params.append("%" + abstract_contains.lower() + "%")

    where = " AND ".join(conditions) if conditions else "TRUE"
    query = f"SELECT patent_id FROM patents WHERE {where}"

    with conn.cursor() as cur:
        cur.execute(query, params)
        return [row[0] for row in cur.fetchall()]


# ── 4. Timed filter + EXPLAIN ANALYZE ────────────────────────────────────

def timed_filter_with_explain(conn, classification_prefix):
    print(f"\n{'='*70}")
    print(f"  Pre-filter: classification_prefix=\"{classification_prefix}\"")
    print(f"{'='*70}")

    t0 = time.time()
    ids = filter_patents(conn, classification_prefix=classification_prefix)
    elapsed = time.time() - t0

    print(f"  Matched patent_ids: {len(ids)}")
    print(f"  Wall-clock time:    {elapsed*1000:.2f}ms")

    query = "SELECT patent_id FROM patents WHERE classification LIKE %s"
    param = classification_prefix + "%"

    print(f"\n  EXPLAIN ANALYZE (index forced via enable_seqscan=off):")
    with conn.cursor() as cur:
        cur.execute("SET enable_seqscan = off")
        cur.execute("EXPLAIN ANALYZE " + query, (param,))
        for row in cur.fetchall():
            print(f"    {row[0]}")
        cur.execute("SET enable_seqscan = on")


# ── 5. Status view ──────────────────────────────────────────────────────

def print_status(conn):
    print(f"\n{'='*70}")
    print("  INDEX STATUS DASHBOARD")
    print(f"{'='*70}")

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM patents")
        total = cur.fetchone()[0]
        print(f"\n  Total patents indexed: {total}")

        cur.execute("""
            SELECT index_status, count(*)
            FROM patents
            GROUP BY index_status
            ORDER BY count(*) DESC
        """)
        print("\n  By status:")
        for status, count in cur.fetchall():
            print(f"    {status:20s} {count:>6}")

        cur.execute("""
            SELECT classification, count(*) AS cnt
            FROM patents
            GROUP BY classification
            ORDER BY cnt DESC
            LIMIT 10
        """)
        print("\n  Top 10 classifications:")
        for cls, count in cur.fetchall():
            print(f"    {cls:20s} {count:>6}")

        cur.execute("SELECT max(indexed_at) FROM patents")
        latest = cur.fetchone()[0]
        print(f"\n  Most recent indexed_at: {latest}")

    print(f"\n{'='*70}")


# ── Main ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = get_connection()

    create_schema(conn)
    load_patents(conn, DATA_DIR)
    print_status(conn)

    timed_filter_with_explain(conn, "B60B")
    timed_filter_with_explain(conn, "B60B27")

    conn.close()
