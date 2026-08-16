"""Phase B: build the LanceDB table from data/raw/*.jsonl.

Reads raw OpenAlex responses, reconstructs abstracts, cleans, embeds, and upserts
into a single table scoped by a `subject` column.

One table rather than one database per subject: LanceDB prefiltering already gives
the scoping, so a new subject is a config entry instead of a new connection,
and cross-subject retrieval stays possible.

Usage:
    python -m src.corpus                    # build all subjects
    python -m src.corpus --subject biology
    python -m src.corpus --stats            # report what's in the table
"""

import argparse
import json
import sys

import pyarrow as pa

from . import config, store
from .embedding import embed
from .openalex import reconstruct_abstract

BOILERPLATE = (
    "abstract not available",
    "no abstract available",
    "this article is protected by copyright",
)


def _schema() -> pa.Schema:
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("subject", pa.string()),
            pa.field("title", pa.string()),
            pa.field("abstract", pa.string()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), config.EMBED_DIM)),
            pa.field("publication_year", pa.int32()),
            pa.field("cited_by_count", pa.int32()),
            pa.field("doi", pa.string()),
            pa.field("venue", pa.string()),
            pa.field("authors", pa.string()),
            pa.field("topic", pa.string()),
            pa.field("is_oa", pa.bool_()),
            pa.field("oa_url", pa.string()),
            # The corpus ships inside the
            # installer, so this is redistribution rather than linking.
            pa.field("license", pa.string()),
            pa.field("embed_model", pa.string()),
        ]
    )


def _clean_row(work: dict, subject: str) -> dict | None:
    """Map a raw OpenAlex work to a table row, or None if it should be dropped."""
    abstract = reconstruct_abstract(work.get("abstract_inverted_index")).strip()
    title = (work.get("title") or "").strip()

    if not title or len(abstract) < config.MIN_ABSTRACT_CHARS:
        return None
    if any(marker in abstract[:200].lower() for marker in BOILERPLATE):
        return None

    authorships = work.get("authorships") or []
    authors = "; ".join(
        (a.get("author") or {}).get("display_name", "")
        for a in authorships[:10]
        if (a.get("author") or {}).get("display_name")
    )

    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    topic = (work.get("primary_topic") or {}).get("display_name", "")
    oa = work.get("open_access") or {}
    best_oa = work.get("best_oa_location") or {}
    license_ = best_oa.get("license") or location.get("license") or ""

    return {
        "id": work["id"].rsplit("/", 1)[-1],  # W2741809807, not the full URL
        "subject": subject,
        "title": title,
        "abstract": abstract,
        "text": f"{title}. {abstract}",
        "publication_year": int(work.get("publication_year") or 0),
        "cited_by_count": int(work.get("cited_by_count") or 0),
        "doi": work.get("doi") or "",
        "venue": source.get("display_name") or "",
        "authors": authors,
        "topic": topic,
        "is_oa": bool(oa.get("is_oa")),
        "oa_url": oa.get("oa_url") or "",
        "license": license_,
        "embed_model": config.EMBED_MODEL,
    }


def load_rows(subject: str) -> list[dict]:
    path = config.RAW_DIR / f"{subject}.jsonl"
    if not path.exists():
        print(f"  ! no raw file at {path} -- run `python -m src.openalex` first", file=sys.stderr)
        return []

    rows: list[dict] = []
    seen: set[str] = set()
    dropped = 0
    with path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = _clean_row(json.loads(line), subject)
            if row is None:
                dropped += 1
                continue
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            rows.append(row)

    print(f"  {len(rows)} usable, {dropped} dropped (short/boilerplate abstract)")
    return rows


def build(subjects: list[str], rebuild: bool = False) -> None:
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = store.connect()

    # A schema change (a new column) cannot be merged into an existing table --
    # merge_insert would fail against the old schema. Drop and recreate instead.
    if rebuild and config.TABLE_NAME in store.table_names(db):
        print(f"dropping existing table '{config.TABLE_NAME}' for a clean rebuild\n")
        db.drop_table(config.TABLE_NAME)

    all_rows: list[dict] = []
    for subject in subjects:
        print(f"{subject}:")
        all_rows.extend(load_rows(subject))

    if not all_rows:
        sys.exit("Nothing to build.")

    # The same OpenAlex work can surface under more than one subject -- a
    # contraception study is also biology. Duplicate keys in a merge_insert source
    # are unsafe, so collapse them here, preferring the v1 target subject.
    by_id: dict[str, dict] = {}
    collisions = 0
    for row in all_rows:
        existing = by_id.get(row["id"])
        if existing is None:
            by_id[row["id"]] = row
            continue
        collisions += 1
        if row["subject"] == config.PRIMARY_SUBJECT:
            by_id[row["id"]] = row
    if collisions:
        print(f"\n{collisions} cross-subject duplicate(s) collapsed")
    all_rows = list(by_id.values())

    print(f"\nEmbedding {len(all_rows)} works with {config.EMBED_MODEL} (CPU, be patient)...")
    vectors = embed([r["text"] for r in all_rows])
    for row, vec in zip(all_rows, vectors):
        row["vector"] = vec

    table = pa.Table.from_pylist(all_rows, schema=_schema())

    if config.TABLE_NAME in store.table_names(db):
        tbl = db.open_table(config.TABLE_NAME)
        # Upsert so re-running the build replaces rows instead of duplicating them.
        tbl.merge_insert("id").when_matched_update_all().when_not_matched_insert_all().execute(table)
    else:
        tbl = db.create_table(config.TABLE_NAME, table)

    # Deliberately no create_index(): at a few hundred rows, flat kNN is exact and
    # sub-millisecond. An IVF_PQ index here would only trade away recall.
    print(f"\nTable '{config.TABLE_NAME}' now holds {tbl.count_rows()} rows at {config.DB_PATH}")


def stats() -> None:
    db = store.connect()
    if config.TABLE_NAME not in store.table_names(db):
        sys.exit(f"No table at {config.DB_PATH}. Run the build first.")
    tbl = db.open_table(config.TABLE_NAME)
    rows = tbl.search().limit(10_000).select(
        ["subject", "publication_year", "topic", "embed_model"]
    ).to_list()

    print(f"total rows: {len(rows)}")
    for key in ("subject", "embed_model"):
        counts: dict = {}
        for r in rows:
            counts[r[key]] = counts.get(r[key], 0) + 1
        print(f"\nby {key}:")
        for k, v in sorted(counts.items()):
            print(f"  {k:<28} {v}")

    years: dict = {}
    for r in rows:
        years[r["publication_year"]] = years.get(r["publication_year"], 0) + 1
    print("\nby year:")
    for k, v in sorted(years.items()):
        print(f"  {k}  {'#' * v} {v}")

    topics: dict = {}
    for r in rows:
        topics[r["topic"]] = topics.get(r["topic"], 0) + 1
    print(f"\n{len(topics)} distinct topics; most common:")
    for k, v in sorted(topics.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {v:>3}  {k}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the LanceDB evidence corpus")
    parser.add_argument("--subject", choices=sorted(config.SUBJECTS), help="default: all")
    parser.add_argument("--stats", action="store_true", help="report table contents and exit")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="drop the table first; required after any schema change",
    )
    args = parser.parse_args()

    if args.stats:
        stats()
        return
    build([args.subject] if args.subject else list(config.SUBJECTS), rebuild=args.rebuild)


if __name__ == "__main__":
    main()
