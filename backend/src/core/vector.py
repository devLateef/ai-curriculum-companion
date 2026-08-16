"""Query surface over the LanceDB evidence corpus.

Offline: the only network dependency is Ollama on localhost, for embedding the
query. LanceDB is embedded -- there is no database server.

    from src.core.vector import search
    hits = search("la photosynthese chez les plantes", subject="biology")
"""

import sys
from functools import lru_cache

from . import config, store
from .embedding import embed_one


class CorpusUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _table():
    """Open the table once per process, not once per request.

    Also asserts the index was built with the model about to query it.
    A mismatch raises no error on its own -- it silently returns plausible-looking
    garbage, which is a genuinely miserable bug to track down.
    """
    if not config.DB_PATH.exists():
        raise CorpusUnavailable(
            f"No corpus at {config.DB_PATH}. Run:\n"
            "  python -m src.openalex && python -m src.corpus"
        )
    db = store.connect()
    if config.TABLE_NAME not in store.table_names(db):
        raise CorpusUnavailable(f"Table '{config.TABLE_NAME}' missing at {config.DB_PATH}")

    tbl = db.open_table(config.TABLE_NAME)
    sample = tbl.search().limit(1).select(["embed_model"]).to_list()
    if sample and sample[0]["embed_model"] != config.EMBED_MODEL:
        raise CorpusUnavailable(
            f"Index was built with '{sample[0]['embed_model']}' but config says "
            f"'{config.EMBED_MODEL}'. Re-run `python -m src.corpus`."
        )
    return tbl


FIELDS = [
    "id", "subject", "title", "abstract", "publication_year",
    "cited_by_count", "doi", "venue", "authors", "topic", "is_oa", "oa_url",
    # Explicit: Lance warns that auto-projecting _distance into a selected
    # column set is going away in a future release.
    "_distance",
]


def search_vec(
    vector: list[float],
    k: int = config.DEFAULT_K,
    *,
    subject: str | None = None,
    year_min: int | None = None,
    floor: float = config.DEFAULT_FLOOR,
) -> list[dict]:
    """Retrieve by a precomputed embedding.

    Exists so callers can embed a whole page in one batched Ollama call and then
    search each unit, rather than paying a round trip per unit. On 8 GB the model
    juggling that avoids matters more than the round trips.
    """
    q = _table().search(vector).metric("cosine").limit(config.CANDIDATE_POOL)

    # Prefilter, not postfilter: filtering after retrieval fetches N candidates and
    # can leave zero results.
    predicates = []
    if subject:
        predicates.append(f"subject = '{subject}'")
    if year_min:
        predicates.append(f"publication_year >= {int(year_min)}")
    if predicates:
        q = q.where(" AND ".join(predicates), prefilter=True)

    hits = q.select(FIELDS).to_list()
    return [h for h in hits if h["_distance"] < floor][:k]


def search(
    query: str,
    k: int = config.DEFAULT_K,
    *,
    subject: str | None = None,
    year_min: int | None = None,
    floor: float = config.DEFAULT_FLOOR,
) -> list[dict]:
    """Retrieve evidence for a query, returning [] when nothing clears the floor.

    The floor is the important part. kNN always returns k results, so without a
    distance threshold a claim the corpus knows nothing about still comes back with
    the least-distant abstracts -- and a downstream model will happily render a
    verdict grounded in noise. Returning [] is the correct answer to "is this
    curriculum statement outdated?" when there is no evidence either way.

    Calibrate `floor` with scripts/calibrate.py before trusting it; the default is
    a placeholder, and cross-lingual distances do not sit where monolingual ones do.
    """
    if not query.strip():
        return []
    return search_vec(
        embed_one(query), k, subject=subject, year_min=year_min, floor=floor
    )


def _cli() -> None:
    if len(sys.argv) < 2:
        sys.exit('usage: python -m src.vector "<query>" [subject]')
    subject = sys.argv[2] if len(sys.argv) > 2 else None
    hits = search(sys.argv[1], subject=subject)
    if not hits:
        print("no evidence in corpus above the relevance floor")
        return
    for h in hits:
        print(f"\n[{h['_distance']:.4f}] {h['publication_year']} | {h['topic']}")
        print(f"  {h['title']}")


if __name__ == "__main__":
    _cli()
