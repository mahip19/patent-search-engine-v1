import json
import glob
import statistics

DATA_DIR = "data/patent_data_small"

files = sorted(glob.glob(f"{DATA_DIR}/patents_ipa*.json"))
print(f"{'='*70}")
print(f"PATENT DATA EXPLORATION REPORT")
print(f"{'='*70}\n")

# --- 1. Load everything ---
all_patents = []
file_counts = []
for f in files:
    with open(f) as fh:
        patents = json.load(fh)
        file_counts.append((f.split("/")[-1], len(patents)))
        all_patents.extend(patents)

print(f"1) FILES & COUNTS")
print(f"   Patent files found: {len(files)}")
print(f"   Total patents:      {len(all_patents)}")
print(f"\n   Per-file breakdown:")
for fname, count in file_counts:
    print(f"     {fname}: {count}")

# --- 2. Field coverage ---
print(f"\n{'='*70}")
print(f"2) FIELD COVERAGE (non-null, non-empty)")
print(f"{'='*70}")

all_keys = set()
for p in all_patents:
    all_keys.update(p.keys())
all_keys = sorted(all_keys)

total = len(all_patents)
for key in all_keys:
    present = 0
    for p in all_patents:
        v = p.get(key)
        if v is not None and v != "" and v != [] and v != {}:
            present += 1
    pct = 100.0 * present / total
    print(f"   {key:30s}  {present:>6d}/{total}  ({pct:5.1f}%)")

# --- 3. Value types ---
print(f"\n{'='*70}")
print(f"3) VALUE TYPES")
print(f"{'='*70}")

for key in all_keys:
    types_seen = set()
    for p in all_patents:
        v = p.get(key)
        if v is not None:
            types_seen.add(type(v).__name__)
    print(f"   {key:30s}  {', '.join(sorted(types_seen))}")

print(f"\n   ** claims:              {'list' if isinstance(all_patents[0].get('claims'), list) else 'str'}")
print(f"   ** detailed_description: {'list' if isinstance(all_patents[0].get('detailed_description'), list) else 'str'}")

# --- 4. Example patent ---
print(f"\n{'='*70}")
print(f"4) EXAMPLE PATENT (first patent, all fields)")
print(f"{'='*70}")

example = all_patents[0]
for key in sorted(example.keys()):
    val = example[key]
    if isinstance(val, list):
        print(f"\n   [{key}]  (list, {len(val)} items)")
        for i, item in enumerate(val[:5]):
            preview = str(item)[:200]
            print(f"     [{i}] {preview}")
        if len(val) > 5:
            print(f"     ... ({len(val) - 5} more items)")
    else:
        preview = str(val)[:500]
        print(f"\n   [{key}]  ({type(val).__name__})")
        print(f"     {preview}")

# --- 5. Length stats ---
print(f"\n{'='*70}")
print(f"5) LENGTH STATS (character counts)")
print(f"{'='*70}")

def char_len(val):
    if val is None:
        return 0
    if isinstance(val, list):
        return sum(len(str(item)) for item in val)
    return len(str(val))

for field in ["abstract", "claims", "detailed_description"]:
    lengths = [char_len(p.get(field)) for p in all_patents]
    lengths_nonzero = [l for l in lengths if l > 0]
    if not lengths_nonzero:
        print(f"\n   {field}: no non-empty values")
        continue
    print(f"\n   {field}:")
    print(f"     patents with data: {len(lengths_nonzero)}/{total}")
    print(f"     min:    {min(lengths_nonzero):>10,} chars")
    print(f"     median: {int(statistics.median(lengths_nonzero)):>10,} chars")
    print(f"     mean:   {int(statistics.mean(lengths_nonzero)):>10,} chars")
    print(f"     max:    {max(lengths_nonzero):>10,} chars")
