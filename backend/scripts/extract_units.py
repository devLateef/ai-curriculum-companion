"""Run merge + prefilter across whole PDFs and write the units to jsonl.

Phase 3 needs a pool of *real* extracted units -- for floor recalibration and as
the source of the eval set. Hand-written sentences will not do: production input
is merged PDF lines, longer and hedged, and the whole point of recalibrating is
that those sit differently.

Output is derived from copyrighted PDFs, so data/units/ is gitignored.

    python -m scripts.extract_units                      # all PDFs in curriculum/
    python -m scripts.extract_units --doc contraceptionSVT4
    python -m scripts.extract_units --stats
"""

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.pdf_payload import extract_page  # noqa: E402
from src import config  # noqa: E402
from src.merge import build_units  # noqa: E402
from src.schema import Item  # noqa: E402

CURRICULUM_DIR = config.BACKEND_DIR / "curriculum"
UNITS_DIR = config.DATA_DIR / "units"


def page_count(pdf: Path) -> int:
    out = subprocess.run(
        ["pdfinfo", str(pdf)], capture_output=True, text=True, check=True
    ).stdout
    for line in out.splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    return 0


def extract_doc(pdf: Path, out_dir: Path) -> dict:
    pages = page_count(pdf)
    out_path = out_dir / f"{pdf.stem}.jsonl"
    counts: Counter = Counter()
    kept_total = 0

    with out_path.open("w") as fh:
        for page in range(1, pages + 1):
            items = [Item(**d) for d in extract_page(pdf, page)]
            if not items:
                continue
            for unit in build_units(items):
                counts[unit.dropped_reason or "kept"] += 1
                if not unit.kept:
                    continue
                kept_total += 1
                fh.write(
                    json.dumps(
                        {
                            "doc": pdf.stem,
                            "page": page,
                            "unit_id": f"{pdf.stem}:p{page}:{unit.source_ids[0]}",
                            "text": unit.text,
                            "source_ids": unit.source_ids,
                            "height": unit.height,
                            "words": len(unit.text.split()),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    print(f"{pdf.stem}: {pages} pages -> {kept_total} kept units")
    print(f"   {dict(counts.most_common())}")
    return counts


def stats() -> None:
    if not UNITS_DIR.exists():
        sys.exit(f"No units at {UNITS_DIR}. Run the extraction first.")
    rows = [
        json.loads(line)
        for path in sorted(UNITS_DIR.glob("*.jsonl"))
        for line in path.open()
    ]
    print(f"total units: {len(rows)}")
    for doc, n in Counter(r["doc"] for r in rows).most_common():
        print(f"  {n:>4}  {doc}")
    words = sorted(r["words"] for r in rows)
    print(
        f"\nwords per unit: min={words[0]} median={words[len(words) // 2]} "
        f"p90={words[int(len(words) * 0.9)]} max={words[-1]}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract merged units from curriculum PDFs")
    ap.add_argument("--doc", help="stem of a single PDF, e.g. contraceptionSVT4")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()

    if args.stats:
        stats()
        return

    UNITS_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted(CURRICULUM_DIR.glob("*.pdf"))
    if args.doc:
        pdfs = [p for p in pdfs if p.stem == args.doc]
    if not pdfs:
        sys.exit(f"No PDFs found in {CURRICULUM_DIR}")

    for pdf in pdfs:
        extract_doc(pdf, UNITS_DIR)


if __name__ == "__main__":
    main()
