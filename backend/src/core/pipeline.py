from collections.abc import Callable, Iterator

from . import config
from .classify import classify as ollama_classify
from .embedding import embed
from .merge import Unit, build_units
from .schema import ItemVerdict, PageRequest, Ref, Status
from .vector import search_vec

# (status, rationale, evidence_refs) given the unit text and labelled evidence.
Classifier = Callable[[str, dict[str, dict]], tuple[Status, str | None, list[str]]]


def null_classifier(unit_text: str, evidence: dict[str, dict]) -> tuple[Status, str | None, list[str]]:
    """Retrieval-only classifier: adjudicates nothing, abstains always.

    Kept for testing and for `scripts.eval --retrieval`, which must be able to
    exercise the pipeline without a model. Retrieval failures and generation
    failures look identical from the outside; keeping this path available is what
    keeps them separately diagnosable.
    """
    return "insufficient_evidence", None, []


def _label(hits: list[dict]) -> dict[str, dict]:
    """Label evidence E1..En.

    The model's only referential output is one of these labels, validated against
    what was actually supplied. It never emits a DOI or title -- a small model
    asked for a DOI invents a plausible one. Metadata comes from the index.
    """
    return {f"E{i}": hit for i, hit in enumerate(hits, 1)}


def _to_ref(hit: dict) -> Ref:
    return Ref(
        title=hit.get("title") or "",
        doi=hit.get("doi") or None,
        year=hit.get("publication_year") or None,
        license=hit.get("license") or None,
        source_url=hit.get("oa_url") or None,
    )


def _apply_guards(
    status: Status,
    refs_used: list[str],
    evidence: dict[str, dict],
    doc_year: int | None,
) -> tuple[Status, list[dict]]:
    """Deterministic precision guards.

    The model is never the last line of defence. This matters more at small
    model sizes than it would at large ones.
    """
    # The model can invent labels; keep only ones actually supplied.
    valid = [r for r in refs_used if r in evidence]

    # 1. A flag without evidence is a bug, not a finding.
    if status in ("outdated", "attention") and not valid:
        return "insufficient_evidence", []

    cited = [evidence[r] for r in valid]

    # 2. Evidence predating the textbook cannot show the textbook is out of date.
    if status == "outdated" and doc_year:
        if not any((h.get("publication_year") or 0) > doc_year for h in cited):
            return "attention", cited

    return status, cited


def analyze(
    payload: PageRequest,
    *,
    classify: Classifier = ollama_classify,
    k: int = config.DEFAULT_K,
    floor: float = config.DEFAULT_FLOOR,
) -> Iterator[ItemVerdict]:
    """Yield one verdict per original item, in item order.

    Every item receives a status, including ones the prefilter dropped: the client
    must never infer meaning from absence.
    """
    units: list[Unit] = build_units(payload.items)
    by_id = {item.id: item for item in payload.items}

    kept = [u for u in units if u.kept]

    # Embed the whole page in ONE call, before any generation. On 8 GB this stops
    # Ollama thrashing between bge-m3 and the chat model per unit -- mandatory,
    # not an optimisation.
    vectors = embed([u.text for u in kept]) if kept else []
    # Keyed by identity, not text: two units on a page can legitimately be
    # identical strings, and a text key would collide them.
    vec_by_unit = {id(u): v for u, v in zip(kept, vectors)}

    for unit in units:
        if not unit.kept:
            yield from _emit(unit, by_id, "insufficient_evidence", None, [])
            continue

        hits = search_vec(
            vec_by_unit[id(unit)],
            k=k,
            subject=payload.subject,
            floor=floor,
        )
        if not hits:
            # Below the floor: no model call at all. This is the system working.
            yield from _emit(unit, by_id, "insufficient_evidence", None, [])
            continue

        evidence = _label(hits)
        status, rationale, refs_used = classify(unit.text, evidence)
        status, cited = _apply_guards(status, refs_used, evidence, payload.doc_year)
        yield from _emit(unit, by_id, status, rationale, cited)


def _emit(
    unit: Unit,
    by_id: dict,
    status: Status,
    rationale: str | None,
    cited: list[dict],
) -> Iterator[ItemVerdict]:
    """Expand one unit's verdict across every item it consumed.

    A unit spanning items t7+t8 emits a verdict for both, so highlighting maps back
    to the original geometry.
    """
    refs = [_to_ref(h) for h in cited]
    for item_id in unit.source_ids:
        item = by_id.get(item_id)
        if item is None:
            continue
        payload = item.model_dump()
        payload.pop("status", None)
        payload.pop("rationale", None)
        payload.pop("ref", None)
        yield ItemVerdict(**payload, status=status, rationale=rationale, ref=refs)
