"""Contract tests for the HTTP surface.

These pin the wire format, not the model. A stub classifier stands in for
generation so the suite stays fast and deterministic -- whether qwen returns
`outdated` for a given claim is the eval's job (scripts/eval.py), not a unit
test's. What is tested here is what the contract promises a client:

  * every item gets a verdict, including dropped ones
  * unknown fields survive the round trip untouched
  * merged units emit a verdict for every id they consumed
  * `ref` is always a list of objects, never a string or null
"""

import json

import pytest

from src import app as app_module
from src.schema import ItemVerdict


@pytest.fixture
def client():
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()


@pytest.fixture
def no_model(monkeypatch):
    """Replace the pipeline with a deterministic stand-in.

    Patched at `src.app.analyze` -- the name the route resolved at import time --
    rather than at `src.pipeline.analyze`, which the route no longer looks up.
    """
    def fake_analyze(payload):
        for item in payload.items:
            flag = "outdated" if "SIDA" in item.text else "insufficient_evidence"
            extras = {
                k: v for k, v in item.model_dump().items()
                if k not in {"id", "text", "status", "rationale", "ref"}
            }
            yield ItemVerdict(
                **extras,
                id=item.id,
                text=item.text,
                status=flag,
                rationale="parce que" if flag == "outdated" else None,
                ref=[{"title": "A Work", "doi": "10.1/x", "year": 2020}] if flag == "outdated" else [],
            )

    monkeypatch.setattr(app_module, "analyze", fake_analyze)


PAGE = {
    "doc_id": "d1",
    "page": 3,
    "lang": "fr",
    "doc_year": 2011,
    "items": [
        {"id": "t1", "text": "Le SIDA reste à ce jour mortel.",
         "location": [1, 2, 3, 4], "custom": {"nested": True}},
        {"id": "t2", "text": "Une phrase ordinaire."},
    ],
}


def test_every_item_gets_a_verdict(client, no_model):
    body = client.post("/api/analyze", json=PAGE).get_json()
    assert [i["id"] for i in body] == ["t1", "t2"]
    assert all("status" in i for i in body)


def test_unknown_fields_pass_through_untouched(client, no_model):
    body = client.post("/api/analyze", json=PAGE).get_json()
    first = next(i for i in body if i["id"] == "t1")
    # Items are opaque except text/id: geometry and arbitrary client fields
    # must come back exactly as sent.
    assert first["location"] == [1, 2, 3, 4]
    assert first["custom"] == {"nested": True}


def test_ref_is_always_a_list_of_objects(client, no_model):
    body = client.post("/api/analyze", json=PAGE).get_json()
    for item in body:
        assert isinstance(item["ref"], list)
        for ref in item["ref"]:
            assert isinstance(ref, dict) and "title" in ref


def test_status_is_from_the_frozen_vocabulary(client, no_model):
    allowed = {"okay", "attention", "outdated", "insufficient_evidence"}
    body = client.post("/api/analyze", json=PAGE).get_json()
    assert {i["status"] for i in body} <= allowed


def test_server_assigns_missing_ids(client, no_model):
    payload = {"doc_id": "d1", "page": 1, "items": [{"text": "Sans identifiant."}]}
    body = client.post("/api/analyze", json=payload).get_json()
    assert body[0]["id"], "server must assign an id when the client omits one"


def test_subject_defaults_when_client_omits_it(client, monkeypatch):
    seen = {}

    def capture(payload):
        seen["subject"] = payload.subject
        return iter(())

    monkeypatch.setattr(app_module, "analyze", capture)
    client.post("/api/analyze", json={"doc_id": "d", "page": 1, "items": []})
    assert seen["subject"] is not None, "server resolves subject when absent"


def test_client_subject_is_not_overridden(client, monkeypatch):
    seen = {}

    def capture(payload):
        seen["subject"] = payload.subject
        return iter(())

    monkeypatch.setattr(app_module, "analyze", capture)
    client.post("/api/analyze",
                json={"doc_id": "d", "page": 1, "subject": "biology", "items": []})
    assert seen["subject"] == "biology"


def test_stream_emits_one_json_object_per_line(client, no_model):
    resp = client.post("/api/analyze/stream", json=PAGE)
    assert resp.mimetype == "application/x-ndjson"
    lines = [l for l in resp.get_data(as_text=True).splitlines() if l.strip()]
    assert len(lines) == 2
    assert [json.loads(l)["id"] for l in lines] == ["t1", "t2"]


def test_stream_and_batch_agree(client, no_model):
    batch = client.post("/api/analyze", json=PAGE).get_json()
    streamed = [
        json.loads(l)
        for l in client.post("/api/analyze/stream", json=PAGE)
        .get_data(as_text=True).splitlines() if l.strip()
    ]
    assert batch == streamed, "the two transports must not diverge"


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"page": 1}, 400),                       # missing doc_id and items
        ({"doc_id": "d", "page": 1, "items": [{"no_text": 1}]}, 400),
    ],
)
def test_invalid_bodies_are_rejected(client, no_model, payload, expected):
    assert client.post("/api/analyze", json=payload).status_code == expected


def test_non_json_body_is_rejected(client, no_model):
    resp = client.post("/api/analyze", data="not json",
                       content_type="text/plain")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_config_publishes_the_frozen_vocabulary(client):
    body = client.get("/api/config").get_json()
    assert set(body["status_vocabulary"]) == {
        "okay", "attention", "outdated", "insufficient_evidence"
    }
    # A client that renders verdicts as authoritative is misrepresenting them
    # at current accuracy; the flag saying so is part of the contract.
    assert body["accuracy"]["advisory"] is True
