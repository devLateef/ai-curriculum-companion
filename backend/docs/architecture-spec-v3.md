# Architecture Spec v3 — AI Curriculum Companion

_Supersedes architecture-spec-v2 (deleted 2026-08-16; recoverable from git history).
The v2 §0 decisions are resolved and recorded in §1 below. Substitutions and
knowingly-unvalidated inputs live in `outputs.md`._

**Scope of this document:** the pipeline from **the moment a page payload has been
received** to a set of per-item verdicts. Transport and delivery timing (SSE,
pre-processing, caching) are explicitly deferred until the frontend is ready — see
§2. Everything here is written so that decision can be made later without reopening
this spec.

**Unchanged from v2 and still correct:** the retrieval layer (`embedding.py`,
`vector.py`, `store.py`, `config.py`) is built, verified, and is reused as-is.

---

## 1. Resolved decisions

| # | Decision | Resolution |
|---|---|---|
| 1.1 | Product shape | **Live reader, offline.** Francophone student or teacher; inline flags; no internet. Not a batch audit tool. |
| 1.2 | Target hardware | **4 cores, 8 GB RAM, no GPU.** A low-end school laptop. See §3 — this is the binding constraint on the whole design. |
| 1.3 | Extraction | **Code, not LLM.** Client sends PDF text items; merged into sentence units in code (§5.1). No extraction model call. Reinstating it requires earning its place on the eval set. |
| 1.4 | Status vocabulary | **Frozen at four** (§4). |
| 1.5 | Evidence display | **Metadata only** — title, year, DOI. No snippet, no translation. Changes the response contract; see §4.2. |
| 1.6 | Corpus focus | **Human reproductive and sexual health** for v1 — contraception, puberty, reproduction, STI/HIV. Amended 2026-08-13 from "psychology" to match the curriculum documents actually obtained (§7). Recorded as S-2 in `outputs.md`. |
| 1.7 | Curriculum source | **French SVT 4ème chapters** (puberty, reproduction, contraception) standing in for DRC material. Recorded as S-1 in `outputs.md` — read it before quoting any number. |
| 1.8 | Delivery timing | **Deferred** (§2). Not blocking. |
| 1.9 | Flag scope | **Factual drift only.** Claims contradicted by newer evidence. Dated or harmful *framing* is explicitly out of scope for v1 and recorded as gap G-1 in `outputs.md`. |

---

## 2. What is deliberately deferred

The reader UX question — classify a page on demand versus pre-process the whole
document on upload — is **not decided**, and v3 does not need it decided. The
pipeline is specified as a transport-agnostic generator (§5), so all three plausible
answers consume the same code.

The constraint that will drive that decision, recorded now so it is not rediscovered
later:

> On 4 CPU cores, a 0.8b model needs roughly **3–8 s per classification** once
> prompt processing is counted. A page yielding ~10 units, with prefiltering and the
> floor removing perhaps half, still lands at **15–40 s to fully flag one page**.

That is not "seconds per page." When the frontend is ready, this is likely to force
pre-processing on upload (a textbook is static; verdicts can be cached by document
hash + unit hash). Nothing in this spec should assume it either way.

**Design requirement that follows:** no pipeline module may import Flask, touch
`request`, or write to a response stream. §10.

---

## 3. The hardware cascade

1.2 is the most consequential decision in this document, and several things follow
from it that are easy to miss.

### 3.1 Memory arithmetic

| Item | Resident |
|---|---|
| bge-m3 | ~1.2 GB |
| qwen3.5:0.8b | ~1.0 GB |
| Ollama runtime + KV cache | ~0.5 GB |
| OS + browser + Flask | ~3–4 GB |
| **Total** | **~6–7 GB of 8 GB** |

This fits, but with little headroom.

- Set `OLLAMA_MAX_LOADED_MODELS=2` and confirm both stay resident with `ollama ps`
  under real load. If Ollama evicts between them, every unit pays a model reload.
- **Batching all embeddings before any generation (§5.4) is mandatory, not an
  optimization.** With alternating calls on this machine, thrash is the dominant
  cost.
- Keep `num_ctx: 4096`. Larger buys nothing here and costs KV cache.

### 3.2 Model size is fixed

`qwen3.5:9b` is impossible. A 3b quantized model is marginal at best against the
budget above and should only be attempted if the eval shows 0.8b failing *and*
measurement shows headroom. Assume **0.8b**.

**The consequence that matters:** "use a bigger model" is not an available fix. Any
quality problem must be solved in the corpus, the prompt, or the guards. This
promotes the evidence-type spike (§6) from precaution to blocking step, and makes
the prompt discipline in §8 load-bearing rather than good practice.

Recorded as S-3 in `outputs.md`.

---

## 4. Contract

The server treats each incoming item as **opaque except for two fields**:

- `text` — guaranteed, the extracted line content
- `id` — assign server-side if absent

Every other field passes through untouched and is echoed back unmodified. The server
never parses `location`. This lets the client change its extraction schema without
touching the backend.

### 4.1 Request

```json
{
  "doc_id": "sess-91f2",
  "page": 42,
  "lang": "fr",
  "subject": "psychology",
  "items": [
    {
      "id": "t7",
      "text": "La mémoire de travail a une capacité de sept éléments",
      "location": [72, 310, 468, 326],
      "any_other_field": "passed through"
    }
  ]
}
```

`subject` maps to the existing LanceDB prefilter column. If the client cannot supply
it, the server infers it **once per document**, never per page.

### 4.2 Response — one object per original item

```json
{
  "id": "t7",
  "text": "La mémoire de travail a une capacité de sept éléments",
  "location": [72, 310, 468, 326],
  "any_other_field": "passed through",
  "status": "attention",
  "rationale": "Une phrase, en français.",
  "ref": [
    {
      "title": "...",
      "doi": "10.xxxx/yyyy",
      "year": 2024,
      "license": "cc-by",
      "source_url": "https://..."
    }
  ]
}
```

**Changed from v2:** `ref` objects **no longer carry `snippet`**, per decision 1.5.
Display is metadata-only, which removes the hallucination surface, sidesteps the
reconstructed-abstract punctuation problem, and saves a generation call per shown
reference — which matters on this hardware.

- `ref` is an **array of structured objects**, never a string. One claim can have
  several supporting works, and the client needs the DOI as a field to build a link.
- `status` is present on **every** item, including silent ones. The client must not
  infer meaning from absence.
- A merged unit spanning `t7`+`t8` emits a verdict for **both** ids, so highlighting
  maps back to the original geometry.

### 4.3 Status vocabulary — frozen

| status | set by | meaning | UI |
|---|---|---|---|
| `okay` | model | evidence retrieved, no meaningful divergence | nothing |
| `attention` | model | still taught, but actively evolving or contested | amber underline |
| `outdated` | model | factually superseded, or harmful if taught as-is | red underline |
| `insufficient_evidence` | **floor (code)** or model | corpus cannot adjudicate this claim | nothing |

`insufficient_evidence` is not a failure state — it is the system working. It must be
visually silent but **distinguishable from `okay` in logs and eval**, because the
ratio between them is the honest measure of corpus coverage.

---

## 5. Pipeline

```
payload received
      │
      ├─ 5.1 merge lines → units                    (code)
      ├─ 5.2 prefilter                              (code)
      ├─▶ embedding.py  (bge-m3, ALL units batched)          ✅ BUILT
      ├─▶ vector.search()                                    ✅ BUILT
      ├─ 5.5 floor → insufficient_evidence          (code)   ✅ BUILT
      ├─▶ ollama /api/chat (qwen) per surviving unit
      ├─ 5.7 guards + hydration                     (code)
      │
      └──▶ yields ItemVerdict per original item
```

### 5.0 Interface

```python
def analyze(payload: PageRequest) -> Iterator[ItemVerdict]:
    ...
```

A generator, deliberately. SSE consumes it by streaming each yield; a batch
pre-processor consumes it by draining into a cache; the eval script consumes it
directly. None of them require this signature to change. This is what makes §2's
deferral safe.

### 5.1 Merge (code — replaces LLM extraction)

A PDF text item is **not** a claim. Extractors emit lines that break mid-sentence,
split columns, and include running headers. Embedding `"La mémoire de travail a"`
and `"une capacité de sept éléments"` separately yields two useless vectors.

- Join consecutive items until the text ends in terminal punctuation, **or** a large
  vertical gap / font-size change signals a new block.
- Each unit carries `source_ids: ["t7","t8"]`.
- Drop units under ~8 words, and those matching header / footer / page-number patterns.

### 5.2 Prefilter (code)

Skip headings, exercise prompts, captions, figure labels, pure formulas. These never
reach embedding or the model. On this hardware every unit removed here is 3–8 s
saved, so the prefilter is a performance component, not just a quality one.

### 5.3 Embed — use `embedding.py` as-is

Batch **every unit on the page in one call, before any generation**. See §3.1.

### 5.4 Retrieve — use `vector.search()` as-is

It is the only interface the generation layer needs. **Do not open LanceDB directly
from new code.** `vector.py` asserts the stored `embed_model` matches config at open
time; bypassing it reintroduces the silent-wrong-rankings failure the shared wrapper
exists to prevent.

### 5.5 Floor — built, but recalibrate

`DEFAULT_FLOOR = 0.47` was measured on 32 hand-written French statements. Production
input is merged PDF lines: longer, hedged, with subordinate clauses and textbook
register. Those distances sit differently.

**Recalibrate `scripts/calibrate.py` on real extracted units**, from the substitute
curriculum (S-1) until a DRC document exists. The current number measures the wrong
distribution.

Below floor → `insufficient_evidence`, no model call, done.

### 5.6 Classify (LLM, one call per surviving unit)

The model sees **only** the unit text and up to three labelled evidence snippets. No
location, no passthrough metadata, no DOIs, no other units, no history.

Constrained output via Ollama structured outputs — pass a **JSON schema** as
`format`, not `format: "json"` — validated with Pydantic:

```json
{
  "status": "attention",
  "evidence_refs": ["E1"],
  "rationale": "Le manuel indique X; les données de 2024 établissent Y."
}
```

The model's only referential output is a label (`E1`), validated against the labels
supplied in that prompt. **The model never emits DOIs or titles** — a small model
asked for a DOI invents a plausible one. Metadata reaches the client from the index.

### 5.7 Guards and hydration (code, deterministic)

1. Status other than `okay` / `insufficient_evidence` with empty or invalid
   `evidence_refs` → force `insufficient_evidence`. A flag without evidence is a bug.
2. Evidence `year` older than the textbook's publication year cannot justify
   `outdated` → downgrade to `attention`.
3. Map `E1` → record id → full metadata via LanceDB.
4. Expand the unit verdict across its `source_ids`.

Never let the model be the last line of defence on precision. This matters more at
0.8b than it would at 9b.

---

## 6. Evidence-type spike — blocking, do this first

v2 flagged this as a risk. Under decision 1.2 it becomes **blocking**, because the
usual remedy is unavailable.

Two early assumptions -- that recent reviews exist for these claims, and that
abstracts alone are sufficient to adjudicate them -- hold for **retrieval** and may
break for **adjudication**.

A review abstract typically says *"we survey recent advances in X and discuss
implications."* That is topically close — it will clear the floor — and contains no
sentence that contradicts a textbook claim. The model then receives three on-topic,
evidentially empty passages and is asked for a verdict.

This failure looks like a model problem from the outside. It is not. And per §3.2,
scaling the model is not an option, so a wrong diagnosis here costs the project real
time.

**The test, before any prompt work:** take ten units that clear the floor, read the
retrieved abstracts by eye, and ask whether *a human* could render a verdict from
them alone. If not, no model can, and the fix is corpus-side — guideline documents,
position statements, education research — not model-side.

Same discipline as `--inspect`: corpus problems are obvious to a human and invisible
in aggregate statistics.

---

## 7. Corpus — reproductive health, seeded claim-first

**Nobody publishes review literature on photosynthesis or mitosis because that
content has not drifted.** Seeding the corpus with settled school science produces
retrieval hits and a uniform stream of `okay` verdicts — correct, and worthless.

### 7.1 Why field sampling failed — measured, not assumed

A spike on 2026-08-13 ran ten known-outdated French claims against the
field-sampled corpus. Six abstained outright. Of the four that cleared the floor,
**one** returned evidence a human could rule on.

The decisive finding: **cosine distance cannot separate "adjudicable" from "merely
topical."** A useless hit for the serotonin-depression claim scored 0.383, while a
genuinely useful hit for adolescent depression scored 0.329 — both inside the band
calibration had labelled "genuine match." No threshold separates them, so no floor
tuning fixes this. Combined with §3.2 (no larger model available), corpus
composition is the only lever.

Cause: `primary_topic.field.id` sorted by citation count selects whatever is
*most cited in the field*, which is clinical and epidemiological research — not the
literature that addresses any particular curriculum claim.

### 7.2 Seed by claim, not by field

Enumerate the claims to be adjudicated and pull works that specifically address each,
via `title_and_abstract.search`. The starting drift zone for decision 1.6:

| Area | Seed terms |
|---|---|
| Contraception | long-acting reversible contraception, emergency contraception, contraceptive effectiveness typical use, contraceptive contraindications |
| Puberty | puberty onset secular trend, precocious puberty age, adolescent growth spurt, gynecomastia adolescent prevalence |
| STI / HIV | pre-exposure prophylaxis, undetectable untransmittable, HPV vaccination adolescent, condom effectiveness STI |
| Reproduction | age-related fertility decline, menstrual cycle variability, assisted reproduction outcomes |
| Adolescent health | adolescent pregnancy outcomes, comprehensive sexuality education effectiveness |

Rules:

- Drop `type:review` for seeded claims. The literature that refutes a specific claim
  is often a guideline, position statement, or education-research paper.
- **Acceptance test is the probe, not a count.** At least 7 of 10 probe claims must
  retrieve something a human could rule on, judged by reading. Retrieval counts and
  distance statistics do not measure this — §7.1 is the proof.
- Keep `license` and `source_url` on every record. The corpus ships inside the
  installer, so this is **redistribution, not linking** — sources must be openly
  licensed (OpenAlex CC0, PMC OA subset, DOAJ, PLOS, licence-filtered arXiv).
- Expect and state that the tool is silent over most of a chapter, and over
  historical narrative especially (§7.3). Design property, not defect.
- Reconstructed abstracts lose punctuation fidelity. Under decision 1.5 they are
  never displayed, which retires this risk for the UI but not for the prompt.

### 7.3 Expect a high abstention rate for correct reasons

The obtained documents (S-1) are substantially *historical narrative* — the history
of the condom from Fallopius to Goodyear, biographical sidebars, period quotations.
That content cannot go out of date and cannot be checked against recent literature.

Consequence: `insufficient_evidence` will be the majority verdict on a real page,
and that is correct behaviour. It also means the §5.2 prefilter carries more weight
than a naive reading suggests — every historical paragraph it removes is a model
call saved on a machine where each costs 3–8 s.

---

## 8. Prompt handling

- Prompts live as files (`prompts/classify.txt`), loaded at startup, never inlined.
  Git history on every change.
- Schema first; prose second.
- Few-shot examples do the heavy lifting at 0.8b: 3–4 worked examples, one per
  status, **in French**, including one case where the evidence is irrelevant and the
  correct answer is `insufficient_evidence`.
- Context budget at `num_ctx: 4096` — system ~250 / examples ~500 / context ~150 /
  task ~600 tokens. **Evidence is load-bearing; examples are compressible.** Over
  budget: cut an example, or drop to two evidence records. Never truncate the unit.
- Override Ollama's shipped defaults for `qwen3.5:0.8b` (`temperature: 1`,
  `presence_penalty: 1.5`) — chat-tuned and actively harmful for classification. Set
  `temperature: 0`, `presence_penalty: 0`.
- One unit per call. Batching units into one prompt cross-contaminates verdicts at
  small sizes.

---

## 9. Evaluation

30–40 hand-labeled units **from a real curriculum PDF** (the S-1 substitute for now),
not hand-written statements, with ground-truth status. A script runs the pipeline and
prints precision per status.

Workflow for any prompt or corpus change: edit → run eval → compare to last run →
commit with the numbers in the message. No change lands on vibes.

Weight the eval toward **false positives on `outdated`**. A change that gains recall
but flags correct curriculum content fails review. One wrong `outdated` in front of a
teacher and the tool is finished.

Report `insufficient_evidence` rate separately — it is the coverage metric, and it
must not be optimised down by lowering the floor.

Retrieval failures and generation failures look identical from the outside. The eval
must be runnable **against retrieval alone**, so the two stay separately testable.

### 9.1 Label schema and metrics — amended 2026-08-16 (outputs.md R-9, R-10)

The first label set violated this section in a way that took six experiments to
detect: its two flag-positive labels were both defective, so "precision on
`outdated`" was being measured against noise. Two rules follow, and they are
binding on any future relabel.

**Ground truth records only corpus-independent facts.** `labels_v2.jsonl` stores
`is_claim` (does the unit assert something checkable), `in_scope` (is it inside
the corpus's subject scope), and `true_status` (`okay` | `outdated` |
`contested`), plus `target_sentence` for positives. Whether the *current corpus*
can adjudicate a claim is a property of the system under test and is computed at
eval time. The v1 schema's single `adjudicable` axis conflated the two, which
baked corpus gaps into the ground truth and penalised any model that outperformed
the corpus.

**Exact status match is banned as a headline.** On a label distribution this
abstain-heavy, it rewards silence: R-5 measured a model detecting twice as much
scoring *worse* on it. The metric set is flag recall (over distinct `outdated`
claims), flag precision (flags landing on `outdated` or `contested`), and
false-flag rate reported separately — the last being the error this section
weights heaviest. `contested` units accept a flag or an abstention and are
excluded from the recall denominator. Claims duplicated verbatim across units
(heading plus table of contents) count once.

**Generative backends are re-run.** They are not reproducible at temperature 0
(R-3, ±5 points), so `--runs 3` is the default for any quoted generative number
and any gap smaller than the observed spread is noise.

**Labels need independent review before publication.** The first set was written
without review and was wrong twice.

---

## 10. Structural requirements

- Pipeline logic lives in plain modules importable by the Flask routes, the eval
  script, and whatever transport §2 resolves to. **No pipeline module imports Flask,
  reads `request`, or writes to a stream.** The eval loop dies if the pipeline can
  only be exercised over HTTP — and so does the pre-processing option.
- `analyze()` is a generator (§5.0). Do not collect internally and return a list.
- Reuse `embedding.py`, `vector.py`, `store.py`, `config.py` unchanged. New
  generation code is a **consumer** of `vector.search()`, not a peer of it.
- `config.py` remains the single point of change for retargeting.

---

## 11. Non-goals

- **No tool-calling / agent framework.** Control flow is fixed: every unit is always
  embedded, always searched, always classified. The server orchestrates; the model
  decides nothing about flow.
- **No orchestration library** (LangChain / LlamaIndex).
- **No ANN index** at this corpus size. Revisit above ~100k rows.
- **No online fallback.** Offline is the differentiator.
- **No FastAPI migration.** Single user on localhost; threaded Flask is sufficient.
  Revisit only if the product shape changes from 1.1.
- **No snippet translation.** Decision 1.5.

---

## 12. Sequenced next steps

Ordered so the unknowns capable of invalidating the generation layer resolve first.

1. **Choose and obtain the substitute curriculum** (S-1). Assign an owner and a date.
   The only item that cannot be unblocked by writing code.
2. **Evidence-type spike** (§6). Ten units, read by eye, half a day. Blocking:
   determines whether the corpus needs rebuilding before any prompt work.
3. **Reseed the corpus** per §7 against psychology's drift zone; re-run `--inspect`
   by eye before rebuilding the index.
4. **Merge + prefilter** (§5.1–5.2). Pure code, no model, testable in isolation — and
   the input to step 5, so it comes first.
5. **Recalibrate the floor** on real extracted units (§5.5).
6. **Build the eval set** (§9) from the substitute document.
7. **Verdict generation** (§5.6) + guards (§5.7), prompt as a file, measured against
   the eval set.
8. **Revisit §2** once the frontend is ready: decide pre-processing vs on-demand, and
   build the transport around the existing `analyze()` generator.
