"""Recalibrate the relevance floor against extracted units.

Calibrate against real merged PDF lines, not hand-written sentences: production
input is longer and hedged, and those distances do not sit where clean sentences
do.

Reads the cache written by scripts/measure.py and never re-embeds.

    python -m scripts.calibrate --bands          # read samples per distance band
    python -m scripts.calibrate --sweep          # floor vs labels
    python -m scripts.calibrate --floor 0.45
"""

import argparse
import json
import statistics
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402

UNITS_DIR = config.DATA_DIR / "units"
CACHE = UNITS_DIR / "retrieval.jsonl"
LABELS = UNITS_DIR / "labels_v2.jsonl"


def load_cache() -> list[dict]:
    if not CACHE.exists():
        sys.exit(f"No cache at {CACHE}. Run `python -m scripts.measure` first.")
    return [json.loads(line) for line in CACHE.open()]


def load_labels() -> dict[str, dict]:
    if not LABELS.exists():
        return {}
    return {json.loads(line)["unit_id"]: json.loads(line) for line in LABELS.open()}


def top(row: dict) -> float | None:
    return row["hits"][0]["distance"] if row["hits"] else None


def distribution(rows: list[dict]) -> None:
    ds = sorted(d for r in rows if (d := top(r)) is not None)
    print(f"units measured: {len(ds)}")
    print(
        f"min={ds[0]:.3f}  p10={ds[len(ds) // 10]:.3f}  median={statistics.median(ds):.3f}  "
        f"p90={ds[int(len(ds) * 0.9)]:.3f}  max={ds[-1]:.3f}\n"
    )
    lo, hi = 0.20, 0.75
    step = 0.05
    edge = lo
    while edge < hi:
        n = sum(1 for d in ds if edge <= d < edge + step)
        bar = "#" * round(n / max(len(ds), 1) * 200)
        print(f"  {edge:.2f}-{edge + step:.2f}  {n:>4}  {bar}")
        edge += step


def bands(rows: list[dict], per_band: int, width: float) -> None:
    """Print samples per distance band so adjudicability can be judged by reading."""
    rows = [r for r in rows if top(r) is not None]
    rows.sort(key=top)
    edge = (min(top(r) for r in rows) // width) * width

    while edge < max(top(r) for r in rows):
        chunk = [r for r in rows if edge <= top(r) < edge + width]
        if chunk:
            print("\n" + "=" * 96)
            print(f"BAND {edge:.2f} - {edge + width:.2f}   ({len(chunk)} units)")
            print("=" * 96)
            stride = max(len(chunk) // per_band, 1)
            for r in chunk[::stride][:per_band]:
                h = r["hits"][0]
                print(f"\n  [{h['distance']:.3f}] {r['unit_id']}")
                print(textwrap.fill(r["text"][:300], 92, initial_indent="    CLAIM: ",
                                    subsequent_indent="           "))
                print(f"    EVIDENCE ({h['year']}): {h['title'][:76]}")
                print(textwrap.fill(" ".join(h["abstract"].split())[:260], 92,
                                    initial_indent="           ", subsequent_indent="           "))
        edge += width


def sweep(rows: list[dict], labels: dict) -> None:
    """Sweep candidate floors against the hand labels.

    Scoring recall minus noise alone picks a floor that blocks genuinely
    outdated claims before any model sees them. A floor that scores well while
    suppressing detection is the wrong floor, so the count of rejected
    flag-positive units is a hard gate: no floor that blocks one is suggested,
    whatever else it scores.
    """
    labelled = [(r, labels[r["unit_id"]]) for r in rows if r["unit_id"] in labels]
    if not labelled:
        sys.exit(f"No labels at {LABELS}. Label some units first (see docs).")

    pos = [r for r, lab in labelled if lab["is_claim"] and lab["in_scope"]]
    neg = [r for r, lab in labelled if not (lab["is_claim"] and lab["in_scope"])]
    # Out-of-scope flag-positives are excluded from the gate: the corpus cannot
    # adjudicate them, so blocking them is correct behaviour, not lost recall.
    flagpos = [r for r, lab in labelled
               if lab["true_status"] in ("outdated", "contested") and lab["in_scope"]]
    print(f"labelled: {len(pos)} in-scope claims, {len(neg)} other, "
          f"{len(flagpos)} flag-positive\n")
    print(f"  {'floor':>6}  {'kept':>11}  {'noise':>11}  {'blocked':>8}   note")
    print("  " + "-" * 62)

    best = None
    for floor in [round(0.30 + 0.01 * i, 2) for i in range(36)]:
        kept = sum(1 for r in pos if (d := top(r)) is not None and d < floor)
        noise = sum(1 for r in neg if (d := top(r)) is not None and d < floor)
        blocked = sum(1 for r in flagpos if (d := top(r)) is None or d >= floor)
        recall = kept / max(len(pos), 1)
        leak = noise / max(len(neg), 1)
        # A false flag costs more than a miss, hence the 2x on leak -- applied
        # only among floors that admit every flag-positive.
        score = recall - 2 * leak
        flag = ""
        if blocked == 0 and (best is None or score > best[1]):
            best, flag = (floor, score), " <-"
        print(f"  {floor:>6.2f}  {kept:>4}/{len(pos):<6}  {noise:>4}/{len(neg):<6}  "
              f"{blocked:>4}/{len(flagpos):<3}{flag}")

    if best is None:
        print("\n  NO FLOOR admits every flag-positive unit. The floor cannot be fixed by "
              "\n  tuning alone -- retrieval or unit granularity has to change first.")
        return
    print(f"\n  suggested floor: {best[0]:.2f}")
    print("  (gated on admitting every flag-positive; then noise weighted 2x recall)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Recalibrate the floor on real units")
    ap.add_argument("--bands", action="store_true", help="print samples per band to read")
    ap.add_argument("--per-band", type=int, default=3)
    ap.add_argument("--width", type=float, default=0.05)
    ap.add_argument("--sweep", action="store_true", help="floor sweep against labels")
    ap.add_argument("--floor", type=float, help="report coverage at a candidate floor")
    args = ap.parse_args()

    rows = load_cache()

    if args.bands:
        bands(rows, args.per_band, args.width)
        return
    if args.sweep:
        sweep(rows, load_labels())
        return
    if args.floor:
        ds = [d for r in rows if (d := top(r)) is not None]
        n = sum(1 for d in ds if d < args.floor)
        print(f"floor {args.floor}: {n}/{len(ds)} units clear it ({n / len(ds):.0%})")
        return

    distribution(rows)


if __name__ == "__main__":
    main()
