"""HTTP surface for the page-analysis contract.

The only module that imports Flask. Nothing in the pipeline may import it, read
`request`, or write to a response stream, so that the evaluation harness and any
future pre-processing pass can drive `analyze()` directly. This file is a thin
adapter: parse JSON into a `PageRequest`, drain or stream the generator, and
serialise the verdicts back.

JSON in, JSON out. PDF handling, text extraction and highlighting belong to the
client; the server treats each item as opaque except for `text` and `id`.

    POST /api/analyze         one page in, verdicts out (waits for the whole page)
    POST /api/analyze/stream  the same, NDJSON, one verdict per line as it lands
    GET  /api/health          model + corpus readiness
    GET  /api/config          the knobs a client needs to display honestly

Run:  ./venv/bin/python main.py       (or: flask --app src.app run)
"""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterator

import httpx
from flask import Flask, Response, jsonify, request
from pydantic import ValidationError

from ..core import config
from ..core.pipeline import analyze
from ..core.schema import PageRequest
from ..core.store import connect, table_names

log = logging.getLogger(__name__)

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

# The client is served from a separate origin during development (Vite on :5173),
# so browser calls are cross-origin. Implemented by hand rather than pulling in
# flask-cors: two headers do not justify a dependency in an offline-first tool.
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
).split(",")


@app.after_request
def _cors(resp: Response) -> Response:
    origin = request.headers.get("Origin")
    if origin and origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    return resp


def _error(message: str, status: int, **extra) -> tuple[Response, int]:
    return jsonify({"error": message, **extra}), status


def _parse() -> PageRequest:
    """Body -> PageRequest. Raises ValidationError or ValueError with a usable message."""
    body = request.get_json(silent=True)
    if body is None:
        raise ValueError("body must be JSON and Content-Type must be application/json")
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object, not a list")

    # Assign ids before validation so a client that sends only text still gets
    # a stable handle back, and so verdicts can be mapped onto the items they
    # were derived from.
    items = body.get("items")
    if isinstance(items, list):
        for i, item in enumerate(items):
            if isinstance(item, dict) and not item.get("id"):
                item["id"] = f"i{i}"
    return PageRequest.model_validate(body)


def _resolve_subject(payload: PageRequest) -> PageRequest:
    """Fill in the retrieval prefilter when the client omits it.

    Only one subject is in scope, so this is a configured default rather than an
    inference dressed up as one. Resolved here rather than inside the pipeline
    so that `analyze(payload)` keeps its signature and transport concerns stay
    confined to this module.
    """
    if not payload.subject:
        payload.subject = config.DEFAULT_SUBJECT
    return payload


@app.post("/api/analyze")
def analyze_page():
    """One page in, every verdict out. Blocks until the page is done.

    Latency is the known cost here: roughly 2 model calls for a median page at
    the default floor, several seconds each. Clients that do not want to hold a
    request open that long should use /api/analyze/stream.
    """
    try:
        payload = _parse()
    except ValidationError as exc:
        return _error("invalid request body", 400, details=json.loads(exc.json()))
    except ValueError as exc:
        return _error(str(exc), 400)

    started = time.time()
    try:
        verdicts = [v.model_dump() for v in analyze(_resolve_subject(payload))]
    except httpx.HTTPError as exc:
        # Ollama unreachable or timing out is an availability problem, not a bad
        # request: say so distinctly so a client can retry rather than "fix" its payload.
        log.exception("model backend failure")
        return _error(f"model backend unavailable: {exc}", 503)

    log.info(
        "analyzed doc=%s page=%s items=%d in %.1fs",
        payload.doc_id, payload.page, len(verdicts), time.time() - started,
    )
    return app.response_class(
        json.dumps(verdicts, ensure_ascii=False),
        mimetype="application/json",
    )


@app.post("/api/analyze/stream")
def analyze_page_stream():
    """The same work, streamed as NDJSON -- one verdict object per line.

    `analyze()` is a generator for exactly this reason. Streaming turns a
    multi-second wall into progressive results, which is what makes an on-demand
    reader usable on this hardware.

    Errors mid-stream cannot use an HTTP status: the 200 is already sent. A final
    line carrying an `error` key is emitted instead, so clients must check for it.
    """
    try:
        payload = _parse()
    except ValidationError as exc:
        return _error("invalid request body", 400, details=json.loads(exc.json()))
    except ValueError as exc:
        return _error(str(exc), 400)

    payload = _resolve_subject(payload)

    def lines() -> Iterator[str]:
        try:
            for verdict in analyze(payload):
                yield json.dumps(verdict.model_dump(), ensure_ascii=False) + "\n"
        except httpx.HTTPError as exc:
            log.exception("model backend failure mid-stream")
            yield json.dumps({"error": f"model backend unavailable: {exc}"}) + "\n"

    return Response(
        lines(),
        mimetype="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
def health():
    """Readiness of the two things that can be absent: the corpus and the models.

    Reported separately because they fail differently -- a missing table is a
    build step that was never run, a missing model is a pull that was never done.
    """
    report: dict = {"ok": True, "corpus": {}, "models": {}}

    try:
        db = connect()
        present = config.TABLE_NAME in table_names(db)
        report["corpus"] = {
            "table": config.TABLE_NAME,
            "present": present,
            "rows": db.open_table(config.TABLE_NAME).count_rows() if present else 0,
        }
        report["ok"] &= present
    except Exception as exc:  # noqa: BLE001 - health must never raise
        report["corpus"] = {"present": False, "error": str(exc)}
        report["ok"] = False

    try:
        r = httpx.get(f"{config.OLLAMA_HOST}/api/tags", timeout=3.0)
        r.raise_for_status()
        # Ollama reports an explicit tag ("bge-m3:latest") while config may name
        # the model untagged ("bge-m3"). Compare on the normalised form or an
        # installed model reads as missing and health lies.
        def _tagged(name: str) -> str:
            return name if ":" in name else f"{name}:latest"

        installed = {_tagged(m["name"]) for m in r.json().get("models", [])}
        wanted = {"chat": config.CHAT_MODEL, "embed": config.EMBED_MODEL}
        report["models"] = {
            role: {"name": name, "present": _tagged(name) in installed}
            for role, name in wanted.items()
        }
        report["ok"] &= all(v["present"] for v in report["models"].values())
    except Exception as exc:  # noqa: BLE001
        report["models"] = {"error": f"ollama unreachable at {config.OLLAMA_HOST}: {exc}"}
        report["ok"] = False

    return jsonify(report), (200 if report["ok"] else 503)


@app.get("/api/config")
def runtime_config():
    """What the client needs to render results honestly.

    The status vocabulary is fixed and published here so that clients read it
    rather than hardcoding a private one that drifts from the server.

    The accuracy block is deliberately part of the contract. At this model size
    the system catches a minority of genuinely outdated claims and does emit
    false flags, so a client presenting a verdict as authoritative misrepresents
    it. Lead with the evidence and frame the verdict as advisory.
    """
    return jsonify({
        "chat_model": config.CHAT_MODEL,
        "embed_model": config.EMBED_MODEL,
        "floor": config.DEFAULT_FLOOR,
        "k": config.DEFAULT_K,
        "subject": config.DEFAULT_SUBJECT,
        "status_vocabulary": {
            "okay": {"display": "silent", "meaning": "evidence retrieved, no meaningful divergence"},
            "attention": {"display": "amber underline", "meaning": "still taught, but evolving or contested"},
            "outdated": {"display": "red underline", "meaning": "factually superseded, or harmful as taught"},
            "insufficient_evidence": {"display": "silent", "meaning": "corpus cannot adjudicate this claim"},
        },
        "accuracy": {
            "advisory": True,
            "note": "Verdicts are advisory. Present the retrieved source first and "
                    "frame the verdict as 'worth checking', not as a finding.",
            "measured": "catches a minority of known-outdated claims; false flags occur",
        },
    })


@app.errorhandler(404)
def not_found(_):
    return _error("no such route; see /api/health for what this server exposes", 404)


@app.errorhandler(405)
def wrong_method(_):
    return _error("wrong HTTP method for this route", 405)
