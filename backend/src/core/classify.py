"""Verdict generation via Ollama.

The model sees only the unit text and up to three labelled evidence excerpts. No
location, no passthrough metadata, no DOIs, no other units, no history.

Output is constrained by a JSON schema passed as `format` -- not `format: "json"`,
which only asks for valid JSON and not the right shape -- then validated with
Pydantic. The model's sole referential output is a label (E1); it never emits a
DOI or a title, because a small model asked for a DOI invents a plausible one.
"""

import json
from functools import lru_cache
from pathlib import Path

import httpx
from pydantic import BaseModel, Field, ValidationError

from . import config
from .schema import Status

PROMPT_PATH = config.BACKEND_DIR / "prompts" / "classify.txt"

# Excerpt length per evidence item. Three of these plus the unit and the prompt
# fit inside num_ctx=4096 with room to spare.
EVIDENCE_CHARS = 420
UNIT_CHARS = 700


class Verdict(BaseModel):
    """Field order is load-bearing, not cosmetic.

    Constrained decoding emits properties in schema order, so whatever comes first
    is chosen with no reasoning behind it. Putting `rationale` first makes the model
    state what the evidence actually says before committing to a label -- a poor
    man's chain of thought that costs nothing and stays inside the JSON constraint.

    With `status` first, an 0.8b model collapsed onto "attention" for 6 of 8 test
    units while writing rationales that described insufficient evidence.
    """

    # All three are required with no defaults. A field carrying a default drops out
    # of the schema's `required` list, and constrained decoding then skips it --
    # which silently returned empty rationales and defeated the ordering above.
    rationale: str = Field(min_length=1)
    evidence_refs: list[str]
    status: Status


@lru_cache(maxsize=4)
def system_prompt(path: Path | None = None) -> str:
    """Loaded once per file. Prompts live in files so git tracks every change.

    The path is overridable so an English prompt can be paired with a translated
    claim: feeding English text into the French prompt mixes languages inside one
    context and confounds any measurement of whether translation helps.
    """
    path = path or PROMPT_PATH
    if not path.exists():
        raise FileNotFoundError(f"Missing prompt file: {path}")
    return path.read_text(encoding="utf-8")


# Field labels must match the prompt's language; mixing them inside one context is
# the confound that made an earlier translation test unreadable.
LABELS = {
    "fr": ("AFFIRMATION DU MANUEL", "PREUVES", "REPONSE (JSON)"),
    "en": ("TEXTBOOK STATEMENT", "EVIDENCE", "REPLY (JSON)"),
}


def build_user_message(unit_text: str, evidence: dict[str, dict], lang: str = "fr") -> str:
    stmt, ev, reply = LABELS.get(lang, LABELS["fr"])
    lines = [f"{stmt}:\n{unit_text[:UNIT_CHARS]}\n", f"{ev}:"]
    for label, hit in evidence.items():
        abstract = " ".join((hit.get("abstract") or "").split())[:EVIDENCE_CHARS]
        lines.append(f"[{label}] ({hit.get('publication_year') or hit.get('year')}) {abstract}")
    lines.append(f"\n{reply}:")
    return "\n".join(lines)


def classify(
    unit_text: str,
    evidence: dict[str, dict],
    *,
    model: str | None = None,
    timeout: float = 180.0,
    prompt_path: Path | None = None,
    lang: str = "fr",
) -> tuple[Status, str | None, list[str]]:
    """Return (status, rationale, evidence_refs). Falls back to abstention on error.

    Any failure -- transport, malformed output, schema violation -- yields
    insufficient_evidence. A verdict the system cannot stand behind must not reach
    the reader, and abstention is the safe direction.
    """
    payload = {
        "model": model or config.CHAT_MODEL,
        "stream": False,
        "format": Verdict.model_json_schema(),
        # Mandatory. qwen3.5 is a thinking model, and with thinking enabled it
        # spends minutes producing reasoning and returns an EMPTY content field:
        # measured at 193s and no answer, against 9.5s with it off.
        "think": False,
        "options": {
            # Ollama ships this model chat-tuned (temperature 1,
            # presence_penalty 1.5), which is actively harmful for classification.
            "temperature": 0,
            "presence_penalty": 0,
            "top_p": 1.0,
            "num_ctx": config.NUM_CTX,
            "num_predict": 256,
        },
        "messages": [
            {"role": "system", "content": system_prompt(prompt_path)},
            {"role": "user", "content": build_user_message(unit_text, evidence, lang)},
        ],
    }

    try:
        resp = httpx.post(f"{config.OLLAMA_HOST}/api/chat", json=payload, timeout=timeout)
        resp.raise_for_status()
        content = resp.json()["message"]["content"]
        verdict = Verdict.model_validate_json(content)
    except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError):
        return "insufficient_evidence", None, []

    rationale = verdict.rationale.strip() or None
    return verdict.status, rationale, verdict.evidence_refs
