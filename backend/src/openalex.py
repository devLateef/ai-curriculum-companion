"""Phase A: fetch works from OpenAlex into data/raw/<subject>.jsonl.

This phase is deliberately separate from corpus.py. You will re-run the build many
times while tuning the embedded text, the cleaning rules, or the model; none of
that should re-hit the API. Raw responses are stored verbatim so Phase B can change
its mind about cleaning without a re-fetch.

Usage:
    python -m src.openalex                        # all subjects
    python -m src.openalex --subject biology
    python -m src.openalex --inspect biology      # eyeball reconstructed abstracts
"""

import argparse
import json
import math
import sys
import time
from pathlib import Path

import httpx

from . import config

SELECT = ",".join(
    [
        "id",
        "doi",
        "title",
        "abstract_inverted_index",
        "publication_year",
        "type",
        "cited_by_count",
        "is_retracted",
        "language",
        "primary_topic",
        "authorships",
        "primary_location",
        "best_oa_location",
        "open_access",
    ]
)


def reconstruct_abstract(inverted_index: dict | None) -> str:
    """Rebuild plain text from OpenAlex's abstract_inverted_index.

    OpenAlex ships abstracts as a word -> [positions] map rather than text, for
    copyright reasons. Round-tripping loses some punctuation fidelity, which is
    harmless for embedding but means the result should not be shown as a verbatim
    quote.
    """
    if not inverted_index:
        return ""
    positioned = sorted(
        (pos, word) for word, positions in inverted_index.items() for pos in positions
    )
    return " ".join(word for _, word in positioned)


def _build_filter(fields: list[str], year: int) -> str:
    return ",".join(
        [
            f"primary_topic.field.id:{'|'.join(fields)}",
            f"type:{config.WORK_TYPE}",
            "has_abstract:true",
            "is_retracted:false",
            f"language:{config.LANGUAGE}",
            f"publication_year:{year}",
        ]
    )


def _fetch_page(
    client: httpx.Client,
    filter_str: str,
    cursor: str,
    per_page: int,
    sort: str = "cited_by_count:desc",
) -> dict:
    resp = client.get(
        config.OPENALEX_BASE,
        params={
            "filter": filter_str,
            "select": SELECT,
            "sort": sort,
            "per-page": per_page,
            "cursor": cursor,
            "mailto": config.MAILTO,
        },
    )
    resp.raise_for_status()
    return resp.json()


def _load_seen(out_path: Path) -> set[str]:
    """Ids already written, so a re-run resumes instead of duplicating."""
    seen: set[str] = set()
    if not out_path.exists():
        return seen
    with out_path.open() as fh:
        for line in fh:
            try:
                seen.add(json.loads(line)["id"])
            except (json.JSONDecodeError, KeyError):
                continue
    print(f"  resuming: {len(seen)} works already in {out_path.name}")
    return seen


def _seed_filter(term: str) -> str:
    return ",".join(
        [
            f"title_and_abstract.search:{term}",
            "has_abstract:true",
            "is_retracted:false",
            f"language:{config.LANGUAGE}",
            f"publication_year:>{config.SEED_YEAR_MIN}",
        ]
    )


def fetch_seeded(subject: str, spec: dict, out_dir: Path) -> int:
    """Claim-first fetch: one search per seed term, top N by relevance.

    No `type:` filter -- restricting to reviews collapses these searches and drops
    exactly the primary studies and guidelines that adjudicate a specific claim.

    No year stratification either. Field mode stratifies to stop citation counts
    biasing the sample toward older work, but here ordering is by relevance and
    recency is already bounded by SEED_YEAR_MIN; stratifying would only defeat the
    relevance ranking.
    """
    out_path = out_dir / f"{subject}.jsonl"
    seen = _load_seen(out_path)
    per_seed = spec["per_seed"]
    written = 0

    with httpx.Client(timeout=60.0) as client, out_path.open("a") as fh:
        for term in spec["seeds"]:
            got, cursor = 0, "*"
            while cursor and got < per_seed:
                try:
                    data = _fetch_page(
                        client,
                        _seed_filter(term),
                        cursor,
                        min(200, per_seed - got),
                        sort="relevance_score:desc",
                    )
                except httpx.HTTPError as exc:
                    print(f"  ! '{term}': request failed ({exc}) -- skipping", file=sys.stderr)
                    break

                results = data.get("results", [])
                if not results:
                    break
                for work in results:
                    if work["id"] in seen:
                        got += 1  # a duplicate still counts against this seed's quota
                        continue
                    seen.add(work["id"])
                    # Record which seed matched, so --inspect can expose terms that
                    # returned nothing useful.
                    work["_seed"] = term
                    fh.write(json.dumps(work) + "\n")
                    written += 1
                    got += 1
                fh.flush()
                cursor = data.get("meta", {}).get("next_cursor")
                time.sleep(0.15)

            print(f"  {got:>3} | {term}")

    print(f"  -> {written} new works written to {out_path}")
    return written


def fetch_subject(subject: str, spec: dict, out_dir: Path) -> int:
    """Fetch a year-stratified sample for one subject. Returns rows written.

    Stratifying by year matters: sorting the whole 2018+ pool by citation count
    would skew the corpus toward 2018-2020, since citations accrue over time. That
    is backwards for a tool whose job is spotting outdated content.
    """
    years = config.YEARS
    per_year = math.ceil(spec["target"] / len(years))
    out_path = out_dir / f"{subject}.jsonl"

    seen = _load_seen(out_path)
    written = 0
    with httpx.Client(timeout=60.0) as client, out_path.open("a") as fh:
        for year in years:
            filter_str = _build_filter(spec["fields"], year)
            cursor, got = "*", 0
            while cursor and got < per_year:
                page_size = min(200, per_year - got)
                try:
                    data = _fetch_page(client, filter_str, cursor, page_size)
                except httpx.HTTPError as exc:
                    print(f"  ! {year}: request failed ({exc}) -- skipping year", file=sys.stderr)
                    break

                results = data.get("results", [])
                if not results:
                    break
                for work in results:
                    if work["id"] in seen:
                        continue
                    seen.add(work["id"])
                    fh.write(json.dumps(work) + "\n")
                    written += 1
                    got += 1
                fh.flush()
                cursor = data.get("meta", {}).get("next_cursor")
                time.sleep(0.15)  # stay well inside the 10 req/s limit

            print(f"  {year}: +{got}")

    print(f"  -> {written} new works written to {out_path}")
    return written


def inspect(subject: str, limit: int = 20) -> None:
    """Print reconstructed abstracts so corpus problems can be caught by eye.

    Aggregate statistics hide bad corpora; a human reading twenty abstracts does
    not. Run this before embedding anything.
    """
    path = config.RAW_DIR / f"{subject}.jsonl"
    if not path.exists():
        sys.exit(f"No raw file at {path}. Run the fetch first.")
    with path.open() as fh:
        for i, line in enumerate(fh):
            if i >= limit:
                break
            work = json.loads(line)
            abstract = reconstruct_abstract(work.get("abstract_inverted_index"))
            topic = (work.get("primary_topic") or {}).get("display_name", "?")
            seed = work.get("_seed")
            head = f"\n[{i + 1}] {work['publication_year']} | {topic} | cites={work['cited_by_count']}"
            print(head + (f"\n    seed: {seed}" if seed else ""))
            print(f"    {work.get('title')}")
            print(f"    {abstract[:300]}{'...' if len(abstract) > 300 else ''}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch OpenAlex works into data/raw/")
    parser.add_argument("--subject", choices=sorted(config.SUBJECTS), help="default: all")
    parser.add_argument("--inspect", metavar="SUBJECT", help="print reconstructed abstracts and exit")
    args = parser.parse_args()

    if args.inspect:
        inspect(args.inspect)
        return

    if not config.MAILTO:
        sys.exit(
            "OPENALEX_MAILTO is not set. OpenAlex's polite pool requires a contact "
            "address; without it requests are throttled.\n"
            "  export OPENALEX_MAILTO=name@example.com"
        )

    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    subjects = [args.subject] if args.subject else list(config.SUBJECTS)
    for subject in subjects:
        spec = config.SUBJECTS[subject]
        mode = spec.get("mode", "fields")
        print(f"{subject}: ({mode})")
        if mode == "seeds":
            fetch_seeded(subject, spec, config.RAW_DIR)
        else:
            fetch_subject(subject, spec, config.RAW_DIR)


if __name__ == "__main__":
    main()
