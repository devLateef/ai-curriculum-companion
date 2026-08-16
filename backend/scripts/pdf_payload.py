"""Turn a curriculum PDF page into the payload the client would POST.

The real client extracts text items in the browser with pdf.js. This reproduces
that shape on the backend from `pdftotext -bbox-layout`, so merge and prefilter can
be exercised against genuine PDF structure -- column breaks, running headers,
captions interleaved mid-paragraph -- rather than imagined input.

Uses poppler, already present; deliberately no new PDF dependency.

    python -m scripts.pdf_payload curriculum/svt_manual4_puberte.pdf --page 3
    python -m scripts.pdf_payload curriculum/contraceptionSVT4.pdf --page 4 --json
"""

import argparse
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.core.schema import PageRequest  # noqa: E402

NS = {"x": "http://www.w3.org/1999/xhtml"}


def extract_page(pdf: Path, page: int) -> list[dict]:
    """One item per PDF line: text plus [x, y, width, height] in points.

    Height doubles as the font-size proxy that merge uses to spot heading/body
    changes -- on these documents headings run ~18pt against ~10pt body.
    """
    out = subprocess.run(
        ["pdftotext", "-bbox-layout", "-f", str(page), "-l", str(page), str(pdf), "-"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    root = ET.fromstring(out)

    items: list[dict] = []
    for n, line in enumerate(root.iter(f"{{{NS['x']}}}line")):
        words = [w.text or "" for w in line.iter(f"{{{NS['x']}}}word")]
        text = " ".join(w for w in words if w).strip()
        if not text:
            continue
        x0, y0 = float(line.get("xMin")), float(line.get("yMin"))
        x1, y1 = float(line.get("xMax")), float(line.get("yMax"))
        items.append(
            {
                "id": f"p{page}l{n}",
                "text": text,
                "location": [round(x0, 2), round(y0, 2), round(x1 - x0, 2), round(y1 - y0, 2)],
            }
        )
    return items


def build_payload(pdf: Path, page: int, subject: str, doc_year: int | None) -> PageRequest:
    return PageRequest(
        doc_id=pdf.stem,
        page=page,
        lang="fr",
        subject=subject,
        doc_year=doc_year,
        items=extract_page(pdf, page),
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a page payload from a PDF")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--page", type=int, default=1)
    ap.add_argument("--subject", default="reproductive_health")
    # Publication year of the source document. Drives the guard that stops
    # evidence older than the textbook justifying an `outdated` verdict.
    ap.add_argument("--doc-year", type=int, default=2011)
    ap.add_argument("--json", action="store_true", help="emit the payload as JSON")
    args = ap.parse_args()

    if not args.pdf.exists():
        sys.exit(f"No such file: {args.pdf}")

    payload = build_payload(args.pdf, args.page, args.subject, args.doc_year)

    if args.json:
        print(payload.model_dump_json(indent=2))
        return

    print(f"{payload.doc_id} p{payload.page}: {len(payload.items)} items\n")
    for item in payload.items:
        x, y, w, h = item.location
        print(f"  {item.id:<8} h={h:>5.1f} x={x:>6.1f} y={y:>6.1f}  {item.text[:74]}")


if __name__ == "__main__":
    main()
