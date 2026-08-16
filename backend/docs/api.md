# Analysis API

The HTTP surface for page analysis. JSON in, JSON out. **The server never sees the PDF** — text extraction,
rendering and highlighting are the client's job. The server treats every item as
opaque except `text` and `id`.

Run it:

```bash
cd backend
./venv/bin/python main.py          # http://127.0.0.1:5000
```

Check it is alive before anything else:

```bash
curl localhost:5000/api/health
```

---

## The one thing to read before integrating

**Verdicts are advisory, not findings.** On the current model
(`qwen3.5:0.8b`) the system catches roughly one in three known-outdated claims
and does produce false flags. That figure is measured, not estimated.

A UI that renders a red badge saying OUTDATED presents a coin-flip as a fact,
in front of a teacher, about their own material. Lead with the retrieved source
and frame the verdict as something to check:

```
⚠  « Le SIDA reste à ce jour mortel. »

    Worth checking against:
    → CDC Sexually Transmitted Diseases Treatment Guidelines (2015)
      doi:10.1093/cid/civ771

    Model note: evidence suggests this may be superseded.
```

`GET /api/config` returns `accuracy.advisory: true` so this is machine-readable
rather than a convention someone has to remember.

---

## `POST /api/analyze`

One page in, every verdict out. Blocks until the whole page is done — budget
**15–40 s** for a typical page, so show a spinner or use the streaming endpoint
below.

**Request** — `Content-Type: application/json`

```json
{
  "doc_id": "sess-91f2",
  "page": 3,
  "lang": "fr",
  "subject": "reproductive_health",
  "doc_year": 2011,
  "items": [
    {
      "id": "t7",
      "text": "Le SIDA, lui, reste à ce jour mortel.",
      "location": [72, 310, 468, 16],
      "any_other_field": "passed through"
    }
  ]
}
```

| field | required | notes |
|---|---|---|
| `doc_id` | yes | your handle for the document |
| `page` | yes | integer |
| `items` | yes | array; may be empty |
| `items[].text` | yes | the extracted line |
| `items[].id` | no | assigned server-side (`i0`, `i1`, …) if omitted |
| `items[].location` | no | `[x, y, width, height]` in PDF points. Height doubles as a font-size proxy and **improves merging** — send it when you have it |
| `lang` | no | defaults `fr` |
| `subject` | no | corpus prefilter; server fills in its default when absent |
| `doc_year` | no | publication year of the textbook. **Send this.** Without it the guard that stops evidence *older* than the book being used to call the book outdated cannot run |

Any other field on an item is echoed back untouched. Change your extraction
schema freely; the backend does not care.

**Response** — `200`, a JSON **array**, one object per original item, in item order:

```json
[
  {
    "id": "t7",
    "text": "Le SIDA, lui, reste à ce jour mortel.",
    "location": [72, 310, 468, 16],
    "any_other_field": "passed through",
    "status": "outdated",
    "rationale": "Une phrase, en français.",
    "ref": [
      {
        "title": "CDC Sexually Transmitted Diseases Treatment Guidelines",
        "doi": "https://doi.org/10.1093/cid/civ771",
        "year": 2015,
        "license": null,
        "source_url": "https://academic.oup.com/cid/..."
      }
    ]
  }
]
```

Three properties the client can rely on:

- **Every item comes back with a `status`,** including ones the prefilter dropped
  (page numbers, headings, fragments). Never infer meaning from absence.
- **`ref` is always an array of objects** — possibly empty, never a string, never
  null. One claim can cite several works, and you need `doi` as a field to build
  a link.
- **A merged unit emits a verdict for every id it consumed.** If `t7` and `t8`
  were joined into one sentence, both come back with the same verdict, so your
  highlight maps onto the original geometry.

### Status vocabulary — fixed

| status | set by | meaning | UI |
|---|---|---|---|
| `okay` | model | evidence retrieved, no meaningful divergence | nothing |
| `attention` | model | still taught, but evolving or contested | amber underline |
| `outdated` | model | factually superseded, or harmful as taught | red underline |
| `insufficient_evidence` | floor (code) or model | corpus cannot adjudicate | nothing |

`insufficient_evidence` is **not an error** — it is the system declining to
guess, and it is the majority verdict on a normal page. It must be visually
silent. Do not invent statuses; fetch this table from `/api/config` instead.

---

## `POST /api/analyze/stream`

Identical request and identical verdicts, delivered as
`application/x-ndjson` — **one JSON object per line, as each is decided**.

Cheap verdicts (dropped items, below-floor units) arrive immediately; each
model-backed verdict lands 5–9 s later. This is what makes an on-demand reader
usable on this hardware, and it is why the pipeline is a generator.

```
{"id":"t1","status":"insufficient_evidence",...}
{"id":"t2","status":"insufficient_evidence",...}
{"id":"t3","status":"outdated",...}
```

**Error handling differs.** The `200` header is already sent before work begins,
so a mid-stream failure cannot change the status code. It arrives as a final
line with an `error` key instead:

```json
{"error": "model backend unavailable: ..."}
```

Check every line for `error` before treating it as a verdict.

---

## `GET /api/health`

`200` when usable, `503` when not. Corpus and models are reported separately
because they fail for different reasons — a missing table means the corpus build
never ran; a missing model means `ollama pull` never ran.

```json
{
  "ok": true,
  "corpus": {"table": "works", "present": true, "rows": 446},
  "models": {
    "chat":  {"name": "qwen3.5:0.8b", "present": true},
    "embed": {"name": "bge-m3", "present": true}
  }
}
```

## `GET /api/config`

The knobs a client needs to display results honestly: active models, `floor`,
`k`, the status vocabulary, and the `accuracy` block described above.
Fetch it at startup rather than hardcoding the vocabulary.

---

## Errors

| code | when |
|---|---|
| `400` | body is not JSON, is not an object, or fails validation (`details` carries the pydantic errors) |
| `404` / `405` | wrong route or method |
| `503` | Ollama unreachable or timing out (`/api/analyze`), or health check failing |

---

## CORS

`http://localhost:5173` and `http://127.0.0.1:5173` (Vite's default) are allowed
out of the box. Override with `ALLOWED_ORIGINS` as a comma-separated list.

## Notes for the client

- **Send `location`.** Merging falls back to punctuation-only without it, and
  lines that break mid-sentence embed as useless fragments.
- **Send `doc_year`.** It gates a real precision guard.
- **Send whole lines, not words.** The server joins consecutive items into
  claim-sized units itself; pre-splitting defeats it.
- **Expect silence.** Most items on most pages return `insufficient_evidence`.
  That is coverage being honest, not the tool failing.
