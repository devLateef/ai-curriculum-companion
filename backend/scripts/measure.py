"""Embed every extracted unit, retrieve, and cache the result.

Embedding 683 units on 4-8 CPU cores is minutes of work. Calibration and eval both
need the same retrieval output, so it is computed once here and cached; downstream
scripts read the cache and never re-embed.

    python -m scripts.measure                 # writes data/units/retrieval.jsonl
    python -m scripts.measure --limit 100     # quick pass while iterating
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.embedding import embed  # noqa: E402
from src.vector import search_vec  # noqa: E402

UNITS_DIR = config.DATA_DIR / "units"
CACHE = UNITS_DIR / "retrieval.jsonl"
BATCH = 32


# Other jsonl files live alongside the extracted units. Globbing the directory and
# excluding only the cache silently swallowed labels.jsonl, whose rows have no
# "text" key -- the run crashed partway and left a truncated cache that downstream
# scripts then read without complaint.
NOT_UNITS = {"retrieval.jsonl", "labels.jsonl", "labels_v2.jsonl"}


def load_units(limit: int | None) -> list[dict]:
    rows: list[dict] = []
    for path in sorted(UNITS_DIR.glob("*.jsonl")):
        if path.name in NOT_UNITS:
            continue
        for line in path.open():
            row = json.loads(line)
            if "text" not in row:
                sys.exit(f"{path.name} does not look like a units file (row has no 'text')")
            rows.append(row)
    return rows[:limit] if limit else rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Cache retrieval results for extracted units")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--subject", default=config.PRIMARY_SUBJECT)
    args = ap.parse_args()

    units = load_units(args.limit)
    if not units:
        sys.exit(f"No units in {UNITS_DIR}. Run `python -m scripts.extract_units` first.")

    print(f"measuring {len(units)} units against subject={args.subject}")
    started = time.time()

    with CACHE.open("w") as fh:
        for start in range(0, len(units), BATCH):
            batch = units[start : start + BATCH]
            vectors = embed([u["text"] for u in batch])
            for unit, vec in zip(batch, vectors):
                # floor bypassed: calibration is what decides where the floor goes.
                hits = search_vec(vec, k=args.k, subject=args.subject, floor=float("inf"))
                fh.write(
                    json.dumps(
                        {
                            **unit,
                            "hits": [
                                {
                                    "distance": round(h["_distance"], 4),
                                    "title": h["title"],
                                    "year": h["publication_year"],
                                    "doi": h["doi"],
                                    "abstract": h["abstract"][:600],
                                }
                                for h in hits
                            ],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )
            fh.flush()
            done = min(start + BATCH, len(units))
            rate = done / max(time.time() - started, 1e-6)
            print(f"  {done}/{len(units)}  ({rate:.1f} units/s)", flush=True)

    print(f"\nwrote {CACHE} in {time.time() - started:.0f}s")


if __name__ == "__main__":
    main()
