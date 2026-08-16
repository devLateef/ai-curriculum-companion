"""Evaluation harness.

Two modes. `--retrieval` scores the retrieval layer alone against hand labels;
`--full` scores the floor and the classifier together. Retrieval failures and
generation failures are indistinguishable from the outside, so a run that mixes
them cannot say which to fix -- keeping the halves separately scorable is the
point of the split.

Ground truth records only facts about a unit that do not depend on the corpus:

    is_claim      does the unit assert checkable factual content
    in_scope      is it inside the corpus's subject scope
    true_status   okay | outdated | contested (null for non-claims)

Whether the current corpus happens to be able to adjudicate a claim is a
property of the system under test, so it is computed at scoring time and never
stored as ground truth. Conflating the two lets corpus gaps masquerade as
labels, which penalises any model that outperforms the corpus.

Metrics:

    flag recall      flags on outdated units / outdated units
    flag precision   flags on outdated or contested units / all flags
    false-flag rate  flags on correct claims or non-claims
    acceptable rate  responses within each unit's defensible set

Exact status match is deliberately absent. On a label distribution this
abstain-heavy it rewards silence, and a model detecting twice as much can score
worse on it. False-flag rate carries the most weight: flagging correct
curriculum content costs more than missing a problem.

Contested units accept either a flag or an abstention. A flag there is
justified and counts toward precision, but they stay out of the recall
denominator so a cautious model is not punished for a defensible silence.

Generative models are not reproducible even at temperature 0 -- identical runs
vary by several points -- so `--runs N` repeats the eval and reports the spread.
Treat any difference smaller than that spread as noise.

    python -m scripts.eval --retrieval
    python -m scripts.eval --retrieval --floor 0.43     # try a candidate floor
    python -m scripts.eval --full --runs 3
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402

UNITS_DIR = config.DATA_DIR / "units"
CACHE = UNITS_DIR / "retrieval.jsonl"
LABELS = UNITS_DIR / "labels_v2.jsonl"
RUNS_DIR = UNITS_DIR / "runs"

FLAGS = ("outdated", "attention")
FLAGGABLE = ("outdated", "contested")


def load() -> list[tuple[dict, dict]]:
    if not CACHE.exists() or not LABELS.exists():
        sys.exit(f"Need both {CACHE.name} and {LABELS.name}. Run measure + label first.")
    cache = {json.loads(line)["unit_id"]: json.loads(line) for line in CACHE.open()}
    pairs = []
    for line in LABELS.open():
        lab = json.loads(line)
        if "adjudicable" in lab:  # v1 row: normalise to the v2 shape
            lab = {
                "unit_id": lab["unit_id"],
                "is_claim": lab["adjudicable"],
                "in_scope": True,
                "true_status": ("outdated" if lab.get("status") in FLAGS
                                else lab.get("status")),
                "note": lab.get("note", ""),
            }
        row = cache.get(lab["unit_id"])
        if row:
            pairs.append((row, lab))
    return pairs


def retrieval_eval(pairs: list[tuple[dict, dict]], floor: float) -> dict:
    """Score the retrieval layer: does the floor admit the units worth judging?"""
    tp = fp = tn = fn = 0
    misses, leaks, blocked_positives = [], [], []

    for row, lab in pairs:
        dist = row["hits"][0]["distance"] if row["hits"] else None
        passes = dist is not None and dist < floor
        positive = lab["is_claim"] and lab["in_scope"]
        if positive:
            if passes:
                tp += 1
            else:
                fn += 1
                misses.append((dist, row["unit_id"], row["text"][:70]))
                if lab["true_status"] in FLAGGABLE:
                    blocked_positives.append((dist, row["unit_id"], lab["true_status"]))
        else:
            if passes:
                fp += 1
                leaks.append((dist, row["unit_id"], row["text"][:70]))
            else:
                tn += 1

    pos, neg = tp + fn, fp + tn
    recall = tp / pos if pos else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    abstain_rate = (fn + tn) / len(pairs) if pairs else 0.0

    print(f"floor {floor}   |   {len(pairs)} labelled units ({pos} in-scope claims, {neg} other)\n")
    print(f"  recall     {recall:>6.1%}   ({tp}/{pos} in-scope claims admitted)")
    print(f"  precision  {precision:>6.1%}   ({tp}/{tp + fp} admitted units are in-scope claims)")
    print(f"  noise leak {fp / neg if neg else 0:>6.1%}   ({fp}/{neg} non-claims admitted)")
    # Reported separately and never optimised down: this is the coverage
    # metric, not an error rate.
    print(f"  abstain    {abstain_rate:>6.1%}   ({fn + tn}/{len(pairs)}) -- coverage signal, not a failure")

    # The floor is calibrated on claims worth judging, which selects against
    # short flag-positive ones. This is the check that catches that.
    if blocked_positives:
        print(f"\n  FLOOR BLOCKS DETECTION ({len(blocked_positives)}) -- "
              "outdated/contested units that never reach a model:")
        for d, uid, st in sorted(blocked_positives):
            print(f"    [{d:.3f}] {st:<9} {uid}")

    if misses:
        print(f"\n  MISSES ({len(misses)}) -- in-scope claims rejected:")
        for d, uid, text in sorted(misses):
            print(f"    [{d:.3f}] {uid}\n           {text}")
    if leaks:
        print(f"\n  LEAKS ({len(leaks)}) -- non-claims admitted; these reach the model:")
        for d, uid, text in sorted(leaks):
            print(f"    [{d:.3f}] {uid}\n           {text}")

    return {
        "date": str(date.today()),
        "mode": "retrieval",
        "floor": floor,
        "embed_model": config.EMBED_MODEL,
        "labelled": len(pairs),
        "recall": round(recall, 4),
        "precision": round(precision, 4),
        "noise_leak": round(fp / neg if neg else 0, 4),
        "abstain_rate": round(abstain_rate, 4),
        "blocked_flag_positives": len(blocked_positives),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }


def acceptable(lab: dict, got: str) -> bool:
    """The set of responses that are defensible for a unit."""
    status = lab["true_status"]
    if not lab["is_claim"] or not lab["in_scope"]:
        return got == "insufficient_evidence"
    if status == "okay":
        return got in ("okay", "insufficient_evidence")
    if status == "outdated":
        return got in FLAGS
    if status == "contested":
        return True  # flag justified, abstention defensible, okay arguable
    return got == "insufficient_evidence"


def run_once(pairs: list[tuple[dict, dict]], floor: float) -> dict:
    from src.classify import classify as run_classify
    from src.pipeline import _apply_guards, _label

    rows = []
    for row, lab in pairs:
        dist = row["hits"][0]["distance"] if row["hits"] else None
        if dist is None or dist >= floor:
            got = "insufficient_evidence"  # never reaches the model
        else:
            evidence = _label([{**h, "publication_year": h["year"]} for h in row["hits"]])
            got, _, used = run_classify(row["text"], evidence)
            got, _ = _apply_guards(got, used, evidence, doc_year=2011)
        rows.append((row, lab, got))
        print(".", end="", flush=True)
    print()

    outdated = [(r, l, g) for r, l, g in rows if l["true_status"] == "outdated"]
    # A claim repeated verbatim (chapter heading + table of contents) is one
    # claim; counting both would inflate recall with a free duplicate.
    distinct = [x for x in outdated if "duplicate_of" not in x[1]]
    flagged = [(r, l, g) for r, l, g in rows if g in FLAGS]
    justified = [x for x in flagged if x[1]["true_status"] in FLAGGABLE]
    false_flags = [x for x in flagged if x[1]["true_status"] not in FLAGGABLE]
    negatives = [(r, l, g) for r, l, g in rows
                 if l["true_status"] == "okay" or not l["is_claim"]]
    ok_rate = sum(1 for r, l, g in rows if acceptable(l, g)) / len(rows)
    abstained = sum(1 for _, _, g in rows if g == "insufficient_evidence")

    return {
        "flag_recall": len([x for x in distinct if x[2] in FLAGS]) / len(distinct) if distinct else 0.0,
        "flag_precision": len(justified) / len(flagged) if flagged else 0.0,
        "false_flag_rate": len(false_flags) / len(negatives) if negatives else 0.0,
        "acceptable_rate": ok_rate,
        "abstain_rate": abstained / len(rows),
        "n_outdated": len(distinct),
        "n_flags": len(flagged),
        "n_false_flags": len(false_flags),
        "_missed": [(x[0]["unit_id"], x[2]) for x in outdated if x[2] not in FLAGS],
        "_false": [(x[0]["unit_id"], x[1]["true_status"] or "non-claim", x[2],
                    " ".join(x[0]["text"].split())[:88]) for x in false_flags],
    }


def full_eval(pairs, floor: float, runs: int) -> dict:
    engine = config.CHAT_MODEL
    results = [run_once(pairs, floor) for _ in range(runs)]
    last = results[-1]

    n_claims = sum(1 for _, l in pairs if l["is_claim"] and l["in_scope"])
    print(f"\nfloor {floor}  engine {engine}  |  {len(pairs)} units "
          f"({n_claims} in-scope claims, {last['n_outdated']} distinct outdated claims)"
          f"  |  {runs} run(s)\n")

    keys = ("flag_recall", "flag_precision", "false_flag_rate", "acceptable_rate", "abstain_rate")
    header = f"  {'':<16}" + "".join(f"run {i + 1:<5}" for i in range(runs))
    if runs > 1:
        print(header)
    for k in keys:
        vals = [r[k] for r in results]
        line = f"  {k:<16}" + "".join(f"{v:>7.1%}  " for v in vals)
        if runs > 1:
            line += f"   (min {min(vals):.1%} / max {max(vals):.1%})"
        print(line)

    if last["_missed"]:
        print(f"\n  MISSED OUTDATED (last run, {len(last['_missed'])}):")
        for uid, got in last["_missed"]:
            print(f"    got {got:<22} {uid}")
    if last["_false"]:
        print(f"\n  FALSE FLAGS (last run, {len(last['_false'])}) -- the heaviest-weighted error:")
        for uid, truth, got, text in last["_false"]:
            print(f"    got {got:<10} truth {truth:<10} {uid}\n      {text}")

    agg = {k: round(sum(r[k] for r in results) / runs, 4) for k in keys}
    return {
        "date": str(date.today()),
        "mode": "full",
        "floor": floor,
        "chat_model": config.CHAT_MODEL,
        "labelled": len(pairs),
        "runs": runs,
        **agg,
        **{f"{k}_min": round(min(r[k] for r in results), 4) for k in keys},
        **{f"{k}_max": round(max(r[k] for r in results), 4) for k in keys},
    }


def compare(current: dict, baseline_path: Path) -> None:
    if not baseline_path.exists():
        print(f"\n(no baseline at {baseline_path})")
        return
    base = json.loads(baseline_path.read_text())
    print(f"\n  vs {baseline_path.name} ({base.get('date')}, floor {base.get('floor')}):")
    shared = [k for k, v in current.items()
              if isinstance(v, float) and isinstance(base.get(k), (int, float))
              and not k.endswith(("_min", "_max"))]
    for key in shared:
        now, was = current[key], base[key]
        delta = now - was
        arrow = "+" if delta > 0 else ""
        print(f"    {key:<17} {was:>7.1%} -> {now:>7.1%}   ({arrow}{delta:.1%})")
    for worse in ("noise_leak", "false_flag_rate"):
        if current.get(worse, 0) > base.get(worse, float("inf")):
            print(f"\n  WARNING: {worse} increased. Section 9 weights this above recall --")
            print("  a change that gains recall while flagging more good content fails review.")


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluation harness")
    ap.add_argument("--retrieval", action="store_true", help="score retrieval alone")
    ap.add_argument("--full", action="store_true", help="retrieval + generation (Phase 4)")
    ap.add_argument("--floor", type=float, default=config.DEFAULT_FLOOR)
    ap.add_argument("--runs", type=int, default=1,
                    help="repeat the full eval N times (generative backends are not "
                         "reproducible; identical runs vary by several points)")
    ap.add_argument("--baseline", help="filename under data/units/runs/ to compare against")
    ap.add_argument("--save", metavar="NAME", help="save this run under data/units/runs/")
    args = ap.parse_args()

    if not (args.retrieval or args.full):
        ap.error("choose --retrieval or --full")

    pairs = load()
    result = (full_eval(pairs, args.floor, args.runs) if args.full
              else retrieval_eval(pairs, args.floor))

    if args.baseline:
        compare(result, RUNS_DIR / args.baseline)
    if args.save:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNS_DIR / (args.save if args.save.endswith(".json") else f"{args.save}.json")
        path.write_text(json.dumps(result, indent=2))
        print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
