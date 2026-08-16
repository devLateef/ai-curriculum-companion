"""analyze() contract behaviour, with embedding and retrieval stubbed out.

No Ollama, no LanceDB: these assert the contract (passthrough, id expansion, guards),
not retrieval quality. Retrieval quality is scored by `scripts/eval.py --retrieval`.
"""

import pytest

from src.core import pipeline
from src.core.schema import Item, PageRequest


@pytest.fixture(autouse=True)
def _stub_backends(monkeypatch):
    monkeypatch.setattr(pipeline, "embed", lambda texts: [[0.0] * 8 for _ in texts])
    monkeypatch.setattr(pipeline, "search_vec", lambda *a, **k: [])


def page(*items, **kw) -> PageRequest:
    return PageRequest(doc_id="d1", page=1, subject="reproductive_health", items=list(items), **kw)


def test_every_item_gets_exactly_one_verdict():
    req = page(
        Item(id="t1", text="La puberte est marquee par de nombreux changements du corps humain."),
        Item(id="t2", text="42"),
        Item(id="t3", text="Les hormones ovariennes ont une action contraceptive averee et durable."),
    )
    out = list(pipeline.analyze(req))
    assert [v.id for v in out] == ["t1", "t2", "t3"]
    assert all(v.status for v in out)


def test_passthrough_fields_survive_untouched():
    req = page(
        Item(
            id="t1",
            text="Une phrase suffisamment longue pour passer le prefiltre sans probleme.",
            location=[1.0, 2.0, 3.0, 4.0],
            custom_field="preserved",
        )
    )
    v = list(pipeline.analyze(req))[0]
    dumped = v.model_dump()
    assert dumped["custom_field"] == "preserved"
    assert dumped["location"] == [1.0, 2.0, 3.0, 4.0]


def test_verdict_expands_across_merged_items():
    """A unit spanning t1+t2 emits a verdict for both, so highlighting still maps."""
    req = page(
        Item(id="t1", text="Les dispositifs intra-uterins empechent la", location=[50, 100, 400, 10]),
        Item(id="t2", text="nidation d'un embryon eventuel.", location=[50, 110, 400, 10]),
    )
    out = list(pipeline.analyze(req))
    assert [v.id for v in out] == ["t1", "t2"]
    assert out[0].status == out[1].status


def test_dropped_units_get_insufficient_evidence():
    req = page(Item(id="t1", text="Chapitre 10"))
    v = list(pipeline.analyze(req))[0]
    assert v.status == "insufficient_evidence"
    assert v.ref == []


def test_no_hits_means_no_classifier_call():
    """Below the floor there must be no model call at all."""
    calls = []

    def spy(text, evidence):
        calls.append(text)
        return "okay", None, []

    req = page(Item(id="t1", text="Une affirmation parfaitement plausible mais introuvable ici."))
    list(pipeline.analyze(req, classify=spy))
    assert calls == []


def test_embeds_the_whole_page_in_one_call(monkeypatch):
    """Batching is mandatory on 8 GB, not an optimisation."""
    batches = []
    monkeypatch.setattr(
        pipeline, "embed", lambda texts: batches.append(len(texts)) or [[0.0] * 8 for _ in texts]
    )
    req = page(
        *[
            Item(id=f"t{n}", text=f"Affirmation numero {n} suffisamment longue pour etre gardee ici.")
            for n in range(5)
        ]
    )
    list(pipeline.analyze(req))
    assert batches == [5]


# --- guards -----------------------------------------------------------------

EV = {"E1": {"title": "T", "publication_year": 2020, "doi": "10.1/x"}}


def test_guard_flag_without_evidence_is_downgraded():
    status, cited = pipeline._apply_guards("outdated", [], EV, doc_year=2011)
    assert status == "insufficient_evidence"
    assert cited == []


def test_guard_invented_label_is_rejected():
    status, _ = pipeline._apply_guards("outdated", ["E9"], EV, doc_year=2011)
    assert status == "insufficient_evidence"


def test_guard_evidence_older_than_textbook_cannot_prove_outdated():
    old = {"E1": {"title": "T", "publication_year": 2005}}
    status, cited = pipeline._apply_guards("outdated", ["E1"], old, doc_year=2011)
    assert status == "attention"
    assert len(cited) == 1


def test_guard_allows_outdated_with_newer_evidence():
    status, cited = pipeline._apply_guards("outdated", ["E1"], EV, doc_year=2011)
    assert status == "outdated"
    assert len(cited) == 1


def test_guard_leaves_okay_alone_without_evidence():
    status, _ = pipeline._apply_guards("okay", [], EV, doc_year=2011)
    assert status == "okay"
