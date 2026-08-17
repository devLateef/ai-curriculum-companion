# Outputs, Substitutions and Decision Log

_Started 2026-08-13._

Records decisions where the project knowingly proceeds on a substitute or an
unvalidated input, so the compromise is visible rather than buried in code. Each
entry states what was substituted, why, what it invalidates, and what must be
redone when the real input arrives.

---

## S-1 — Curriculum source: substitute francophone curriculum

**Status:** active substitution — DRC re-run shelved 2026-08-16
**Decided:** 2026-08-13
**Owner:** unassigned — needs one

### What

No DRC curriculum document is available. Development proceeds against a
**published francophone secondary curriculum from a comparable system** (Rwanda,
Senegal, Cameroon, or France), used as a stand-in for DRC material.

### Why

Two things are blocked on real curriculum text and cannot be unblocked by writing
code:

- **Floor recalibration** (`spec-v3` §5.3). `DEFAULT_FLOOR = 0.47` was measured on
  32 hand-written French statements. Production input is merged PDF lines —
  longer, hedged, textbook register — and those distances sit differently.
- **The eval set** (`spec-v3` §9). 30–40 hand-labeled units must come from a real
  document, not hand-written sentences, or the eval measures the wrong thing.

Waiting would stall the entire generation layer. The substitute unblocks both at
the cost of DRC specificity.

### What this invalidates

Results produced against the substitute are **not** evidence that the tool works on
DRC curricula. Specifically:

1. The recalibrated floor is tuned to the substitute's register and vocabulary.
2. Eval precision numbers describe the substitute, not DRC material.
3. Any claim about DRC curriculum accuracy is unsupported until re-run.

Do not present substitute-derived numbers as DRC results — in a report, a demo, or
a panel. State the substitution wherever the numbers appear.

### SHELVED 2026-08-16 — the re-run is not planned

The team judged the substitute documents close enough to DRC material to
proceed without re-running against a DRC source, and shipped on that basis.
The checklist below is **not scheduled**.

**What this does not change:** shelving the re-run does not convert
substitute-derived numbers into DRC evidence. Every figure in this document was
measured on French SVT 4ème chapters. The caveat above still applies to any
report, demo, or panel — state the substitution wherever the numbers appear.

The scripts that would perform these steps (`probe.py`, `sweep_candidates.py`,
`known_claims.py`) were moved to `backend/local/`, untracked, on the same date.
They are recoverable from commit 88fbcb0.

### What would have to be redone if a DRC document does arrive

- [ ] Re-run `scripts/calibrate.py` on units extracted from the DRC document
- [ ] Rebuild the eval set from DRC text; re-label from scratch
- [ ] Re-run the §6 evidence-type spike against DRC claims
- [ ] Re-check that merge rules (`spec-v3` §5.1) hold for its PDF structure
- [ ] Update this entry with the outcome and close it

### Documents in use (obtained 2026-08-13)

Held at `backend/curriculum/`, gitignored. **Copyrighted third-party material** —
local evaluation only; never commit, never ship in the installer.

| File | Pages | Topic |
|---|---|---|
| `svt_manual4_puberte.pdf` | 23 | Puberty |
| `reproductionSVT4.pdf` | 16 | Reproduction |
| `contraceptionSVT4.pdf` | 16 | Contraception |

| Field | Value |
|---|---|
| Source | France, SVT 4ème (lower secondary, ~age 13–14) |
| Origin | Collected from the internet; publisher not established |
| Licence | **Unknown — assume all rights reserved** |
| Format | A4 landscape, Apple Pages export, real text layer (no OCR needed) |
| Why comparable | French-language secondary science, same register and pedagogical framing as DRC material, which is also francophone and French-curriculum-derived |

**Additional caveat beyond S-1's general one:** French *programmes* are revised
frequently, so this material is a good **engineering** substitute (register,
sentence length, PDF structure) but a weak **demonstration** substitute — a
well-maintained curriculum contains little outdated content. If the eval shows too
few genuine detections, source older editions (2005–2010) or African francophone
curricula, where drift is a function of age.

---

## S-2 — Corpus scope: reproductive and sexual health only for v1

**Status:** active narrowing
**Decided:** 2026-08-13 — amended same day (was "psychology / mental health")

v1 targets **human reproductive and sexual health** only: contraception, puberty,
reproduction, STI/HIV. Amended to match the curriculum documents actually obtained
(S-1); a psychology corpus cannot adjudicate a single claim in an SVT chapter on
contraception.

The existing 207 rows (broad biology + psychology) stay in the table — they cost
1.4 MB and the `subject` prefilter isolates them — but they are not a v1 target,
are not evaluated, and did **not** pass the §7.1 spike.

**Invalidates:** any claim of curriculum coverage beyond reproductive health. The
tool will be silent across most of any other chapter. Design property, not defect —
state it before a reviewer discovers it.

**Reversal cost:** low. A `SUBJECTS` edit in `config.py` plus a re-run.

---

## G-1 — Gap: dated and harmful framing is out of scope

**Status:** known gap, deliberate
**Decided:** 2026-08-13

v1 flags **factual drift only** (`spec-v3` §1.9) — claims contradicted by newer
evidence. Language that is dated, gender-essentialist, or stigmatising is **not**
flagged, even where it is arguably the more consequential problem.

Concrete example from the obtained material (`svt_manual4_puberte.pdf`, on
gynecomastia in adolescent boys):

> « Rassurez-vous, vous n'êtes pas en train de vous transformer en fille ! »

Not factually wrong; framing a modern curriculum would not use.

**Why deferred:** it needs a second evidence type — normative sources such as WHO
and UNESCO sexuality-education standards rather than research abstracts — plus a
more complex prompt and a harder labelling rubric. At `qwen3.5:0.8b` (S-3), adding a
second judgement type to one prompt is a material risk to precision on the first.

**Revisit when:** v1 clears its eval on factual drift. For a DRC sexual-health
context this is likely the highest-value extension, so it should not be forgotten.

---

## S-3 — Model size fixed by target hardware

**Status:** active constraint
**Decided:** 2026-08-13

Target is a **4-core / 8 GB laptop with no GPU**, which fixes generation at
`qwen3.5:0.8b`. See `spec-v3` §3 for the memory arithmetic.

**Invalidates:** the common escape hatch of "fix quality by using a bigger model."
It is not available. Any quality problem must be solved in the corpus, the prompt,
or the guards.

**Consequence:** the evidence-type spike (`spec-v3` §6) is a blocking step rather
than a precaution, because a bad corpus cannot be compensated for downstream.

---

## R-1 — Phase 1 gate result: PASS at 7/10 (the minimum)

**Status:** passed, marginally
**Run:** 2026-08-13, `python -m scripts.probe`, 446-row corpus (239 reproductive health)

Claims transcribed verbatim from the SVT 4ème chapters. Judged by reading, per
`spec-v3` §7.2.

| Claim | Result | Evidence |
|---|---|---|
| `growth_spurt` | ✅ pass | *Adolescent Growth Spurt*; *Timing of puberty in boys and girls* — "secular trend towards earlier puberty observed in girls" |
| `gynecomastia` | ✅ pass | *Pubertal gynecomastia incidence among 530,000 boys* — "prevalence varies widely (4%–69%)"; a second cohort gives "up to 65%" |
| `pill_mechanism` | ✅ pass | *Oral Contraceptive Pills*; *Clinical relevance of progestogens* |
| `sti_antibiotics` | ✅ pass | *Doxycycline Prophylaxis* — "early HIV treatment... virtually eliminates transmission risk" |
| `iud` | ❌ fail | *Contraceptive Technology* retrieved (correct source) but its abstract is a definitional list; mechanism absent |
| `ovulation_timing` | ❌ fail | Cycle-variability studies are adjacent; none state the 14-day rule is unreliable |
| `breastfeeding` | ❌ fail | No lactational-amenorrhea literature in corpus at all |
| `hist_fallope` | ✅ abstains | PrEP papers at 0.558+ — correctly unadjudicable |
| `hist_spallanzani` | ✅ abstains | Pregnancy-exercise guideline at 0.618 |
| `hist_aristote` | ✅ abstains | Gynecomastia case report at 0.587 |

**The three failures are seed-list gaps, not an evidence-type failure.** Each has an
obvious missing search term: `intrauterine device mechanism of action`,
`lactational amenorrhea method`, `fertile window variability`. This is a cheap fix
and does **not** trigger the §7.2 escalation to guideline documents or full text.

### Genuine detection confirmed

`gynecomastia` is a real find. The textbook states 70% of boys aged 13–16; the
530,000-boy population study reports a 4–69% range and a second cohort "up to 65%".
The textbook figure sits above the observed range — exactly the class of error this
tool exists to catch, found in real curriculum text against real literature.

### Refinement to the §7.1 distance finding

§7.1 concluded that cosine distance cannot separate adjudicable from merely topical.
That holds, but is now more precise:

| Band | Content |
|---|---|
| 0.305–0.428 | on-topic; adjudicable **or** evidentially empty |
| 0.426–0.471 | on-topic, thin coverage |
| 0.558–0.622 | off-topic (all three historical claims) |

Distance **does** now cleanly separate off-topic from on-topic — a gap between ~0.47
and ~0.56 that the field-sampled corpus did not have. It still **cannot** separate
adjudicable from evidentially-empty *within* the on-topic band: `iud` scores 0.371,
better than several genuine passes, while being unadjudicable.

Implication for Phase 3: a floor near 0.50 should cleanly handle historical narrative
(the bulk of these chapters). Precision within the on-topic band remains a corpus and
guard problem, not a threshold problem.

### Known inefficiency

`corpus.py build()` re-embeds every row from jsonl, so adding four seed terms costs a
full ~16-minute rebuild rather than embedding only the new works. Worth fixing before
seed-list iteration becomes routine.

---

## R-2 — Phase 3: floor recalibrated on real units, 0.47 → 0.39

**Status:** complete
**Run:** 2026-08-13. 683 units extracted from the three SVT chapters (55 pages);
42 hand-labelled; `scripts/calibrate.py --sweep`, `scripts/eval.py --retrieval`.

### The old floor was badly wrong on real input

`DEFAULT_FLOOR = 0.47` was measured on 32 hand-written French sentences. On real
merged PDF units it admitted **16 of 29 non-adjudicable units** — more than half
the noise reaching the model.

| floor | recall | precision | noise leak | abstain |
|---|---|---|---|---|
| **0.39** | 92.3% | **80.0%** | **10.3%** | 64.3% |
| 0.43 | 100% | 56.5% | 34.5% | — |
| 0.47 (old) | 100% | 44.8% | 55.2% | 31.0% |

0.39 costs one adjudicable unit and nearly doubles precision. Chosen per
`spec-v3` §9: one wrong `outdated` in front of a teacher costs more than a miss.

### Secondary effect: the floor is also the latency control

On this corpus the floor decides how many units reach the model, and on 4-core
hardware each call is 3–8s.

| | median calls/page | median page latency |
|---|---|---|
| floor 0.39 | 2 | **6–16s** |
| floor 0.47 | 6 | 18–48s |

Tightening the floor moved a median page from unusable to borderline acceptable —
which materially changes the deferred §2 transport decision. Pre-processing on
upload may no longer be strictly required for a median page, though p90 (6 calls,
18–48s) still argues for it.

### Correction to an earlier prediction

It was previously assumed that long merged units, with pedagogical scaffolding and
subordinate clauses, would embed *worse* than clean sentences. Measurement shows
the opposite — more context retrieves better:

| words in unit | top-1 distance |
|---|---|
| 85 | 0.296 |
| 42 | 0.344 |
| 18 | 0.408 |
| 9 | 0.372 |

The floor therefore had to move **down**, not up.

### Known limitation of the label set

> **SUPERSEDED by R-9/R-10.** The 42 labels were audited and rebuilt as
> `labels_v2.jsonl` (56 units, externally reviewed). Both flag-positive labels
> in this set turned out to be defective, so the floor chosen below rests on a
> benchmark that has since been replaced — see R-10 for the re-measurement.

The 42 labels were produced by reading claim/evidence pairs without domain
expertise, and with prior knowledge of the corpus. They are adequate for
choosing a floor — a relative comparison — but should not be quoted as an absolute
accuracy measure. **A domain reviewer should re-label before any published number.**

### Also observed: `reproductionSVT4` is out of scope

That chapter covers general animal reproduction (frogs, fish, spontaneous
generation) against a *human* reproductive-health corpus. Its units retrieve human
medicine papers at 0.42–0.67 and correctly abstain. Expect near-total silence on
that chapter; it is not a defect, but it makes the contraception and puberty
chapters the only viable demo material.

---

## R-3 — Phase 4 FAILS: qwen3.5:0.8b cannot adjudicate

> **Numbers here are unreliable — see R-8 and R-9.** They were measured against a
> benchmark whose positive class was two defective labels. The reproducibility
> finding (±5 points at temperature 0) survives; the accuracy verdict does not.
> R-10 re-measures on the reviewed label set.

**Status:** blocked, needs a decision
**Run:** 2026-08-14, `scripts/eval.py --full`, 42 labelled units, floor 0.39

### Numbers

| metric | value |
|---|---|
| exact status match | 73.8% (31/42) |
| **always-abstain baseline** | **69.0% (29/42)** |
| flag precision | **0.0%** (0/2 flags justified) |
| flag recall | **0.0%** (0/2 real issues caught) |
| abstain rate | 90.5% |

The model beats a classifier that always answers `insufficient_evidence` by **4.8
points**, while introducing two false flags. On the metric §9 weights heaviest —
false positives on `outdated` — it scores zero.

### The failure is the model, not retrieval or the floor

Tested with the floor bypassed, on four claims known to be outdated. Retrieval
returned the right evidence in every case; the model misread it in every case.

| claim | evidence retrieved | model said |
|---|---|---|
| gynecomastia "70 % des garçons" (d=0.344) | *Adolescent Gynecomastia.* | `attention` — "les preuves ne confirment pas l'existence de ce symptôme" |
| "toutes ces maladies, sauf le SIDA, se soignent facilement" (d=0.388) | *CDC STD Treatment Guidelines* | `insufficient_evidence` — "hors sujet" |
| "les stérilets empêchent la nidation" (d=0.415) | *Contraceptive Technology* | `insufficient_evidence` — "relève de l'histoire médicale" |
| "un seul ovule tous les 28 jours" (d=0.313) | *Characteristics of menstrual cycles…* | `insufficient_evidence` — "un fait historique et une expérience ancienne" |

The last is diagnostic: a present-tense claim about ovarian function, described by
the model as a historical anecdote. The model reaches for "fait historique" as a
universal escape hatch, overfitting Rule 4 and Example 1 of the prompt.

### What was tried

Three prompt revisions, each measured:

1. **Statuses first, prose second, 4 few-shots.** Collapsed to `attention` 6/8;
   every rationale copied Example 2's phrasing verbatim ("Le manuel généralise…").
2. **Explicit ordered decision procedure, `insufficient_evidence` as default,
   history rule promoted.** Still `attention` 6/8, and zero abstentions on two
   clear historical claims.
3. **Schema field order reversed — `rationale` before `status`.** A real finding:
   constrained decoding emits properties in schema order, so with `status` first
   the model picks a label before reasoning. Reversing it flipped the failure mode
   from over-flagging to over-abstaining (safe direction) but did not improve
   accuracy. Also found: fields carrying defaults drop out of the schema's
   `required` list and get skipped entirely, silently producing empty rationales.

Prompt iteration moved the failure mode around. It did not move accuracy.

### Why this is not fixable within current constraints

`spec-v3` §3.2 states that quality problems must be solved in the corpus, prompt,
or guards, since S-3 fixes the model. All three are now exhausted:

- **Corpus** passed its own gate (R-1) and retrieves correct evidence here.
- **Prompt** has been through three measured revisions.
- **Guards** can suppress a bad verdict but cannot manufacture a good one.

The remaining lever is the one S-3 rules out. **Decision 1.2 (4-core/8 GB, hence
0.8b) needs revisiting** — that is an owner decision, not an engineering one.

### Measurement caveats — the numbers above are less precise than they look

Corrected 2026-08-14 after repeating the run. The figures in the table were one
sample and were quoted as if exact. Repeating the identical eval gives:

| repetition | exact match | flag precision | known claims |
|---|---|---|---|
| 1 | 73.8% | 0% (0/2) | — |
| 2 | 73.8% | 0% (0/3) | — |
| 3 | 73.8% | 0% (0/3) | — |
| via `run_all.sh` | 78.6% | 50% (1/2) | 1/4 |

Three things follow:

1. **The model is not reproducible at `temperature: 0`.** Exact match ranges
   73.8–78.6%, flag precision 0–50%, known claims 0–1 of 4. Anything quoted from a
   single run is unreliable to roughly ±5 points.
2. **Flag precision/recall rest on 2–3 items** and cannot detect a small real
   improvement. The `--sweep`/eval workflow in §9 assumes changes are measurable;
   at this sample size they are not.
3. **Before any retry, the eval set needs ~10+ flag-positive units.** This is now
   the blocking prerequisite for measuring Phase 4 at all, ahead of any model change.

The conclusion is unchanged and arguably strengthened: at best the model scores
78.6% against a 69.0% always-abstain baseline, catches 1 of 4 known-outdated claims,
and the metric §9 weights heaviest cannot yet be measured.

Also note the 42 labels were not produced by a domain expert (see R-2).

---

## R-4 — Binary decomposition and translation both fail to rescue 0.8b

**Status:** negative result, cheap to obtain (~5 min), rules out two fixes
**Run:** 2026-08-14, `scripts/experiment_decompose.py`, 6 cases (4 known-outdated + 2 controls)

Tested before committing an hour to a model bakeoff, on the theory that the 4-way
classification might simply be too complex a single step.

| variant | approach | score | calls | seconds |
|---|---|---|---|---|
| **A** | baseline 4-way, French | **3/6** | 6 | 41–52 |
| B | binary yes/no gates, French | 3/6 | 11 | 65 |
| C | 4-way, claim translated to English | 2/6 | 12 | 72 |
| D | binary gates + translation | 2/6 | 13 | 84 |

Neither helps. Decomposition matches the baseline while nearly doubling calls;
translation makes things actively worse.

### Why decomposition fails — the diagnostic observation

Variant D, gate 1, asked only *"does the evidence discuss the same specific subject
as the statement?"* about the gynecomastia claim. The model wrote:

> "The evidence defines gynecomastia as the presence of…"

and answered **false**.

Its own reasoning identifies the evidence as being about gynecomastia, and it then
answers "not on topic". The same contradiction appears in variant A, where the
rationale reads *"les preuves ne confirment pas l'existence de ce symptôme"* about a
paper titled *Adolescent Gynecomastia*.

**The broken step is mapping a reading onto a discrete decision, not the complexity
of the choice.** Simplifying the choice from four options to two therefore changes
nothing. This is why B scores identically to A while costing twice as much: it
trades one error for another (B catches `sti-antibiotics`, which A misses, and
loses `gynecomastia`, which A catches). That is noise, not improvement.

### Why translation fails — the model cannot translate either

Inspecting the intermediate English, produced by the same 0.8b model:

| French | Model's English | Problem |
|---|---|---|
| "des **éponges** pouvaient être utilisées comme contraceptif" | "**sperm** could be used as a contraceptive" | meaning inverted |
| "les dispositifs intra-utérins (**stérilets**)" | "intrauterine devices (**sterilizers**)" | wrong term |
| "dont on parle **peu**" | "a **minor** aspect" | drift |

Variants C and D feed the classifier corrupted input, which fully explains their
lower scores. Translation is a smaller task than adjudication but still beyond
reliable reach at this size.

### Consequence

Three independent software-side approaches have now been tried and measured:
prompt engineering (three revisions, R-3), task decomposition, and language
normalisation. None moved accuracy. Combined with `spec-v3` §3.2 — corpus and
guards already exhausted — there is no remaining lever below changing the model.

**This strengthens rather than weakens the case for the model bakeoff:** the cheap
fixes are now provably exhausted, so the hour is no longer speculative.

---

## R-5 — Model bake-off: size does fix it, and the 42-unit metric is misleading

> **Rankings here need re-testing on the reviewed labels (R-9/R-10);** the
> bake-off has not yet been re-run. The finding that exact match is anti-
> correlated with detection was accepted and acted on — that metric is gone.

**Status:** complete, decision-ready
**Run:** 2026-08-14, `scripts/model_bakeoff.sh`, ~76 min. Full log in `MODEL_BAKEOFF.txt`.
`qwen3.5:1.5b` does not exist in the Ollama library; `2b` used as the mid-size step.

### Detection scales cleanly with model size

| model | known_claims (of 4) | experiment A (of 6, incl. 2 controls) |
|---|---|---|
| qwen3.5:0.8b | 1 | 3 |
| qwen3.5:2b | **2** | **4** |
| qwen3.5:4b | **3** | **5** |

Monotonic on both tests. Retrieval succeeds on all four known claims regardless of
model, so this is a clean read on comprehension. **Model size was the binding
constraint**, exactly as R-3 and R-4 concluded by elimination.

### The 42-unit eval metric is actively misleading — do not use it as a headline

| model | exact match (n=3) | flag precision | abstain |
|---|---|---|---|
| qwen3.5:0.8b | 73.8–78.6% | 33–50% | 85.7% |
| qwen3.5:2b | **69.0–71.4%** | 17–20% | 81.0–83.3% |
| qwen3.5:4b | 73.8–76.2% | 33.3% | 85.7–88.1% |
| *always-abstain* | *69.0%* | *0%* | *100%* |

**2b scores worst on exact match while detecting twice as much as 0.8b.**

The cause is majority-class domination: 29 of 42 units expect
`insufficient_evidence`, so abstaining is worth 69% on its own. 2b flags more units
(5–6 per run against 0.8b's 2–3), which gives it more opportunities to be wrong
across the abstain-heavy majority — its exact match falls even as its detection
improves.

This sharpens R-3's caveat. The problem is not only that the positive set is small;
**the headline metric rewards the behaviour the product needs to avoid.** Exact
match on this label distribution is anti-correlated with detection ability and
should be dropped in favour of the known-claims score until the eval set is
rebalanced.

### Latency cost — this is the real trade

Per model call, measured on the 8-core dev box, with the 4-core target estimated at
roughly 2x:

| model | per call (dev) | per call (4-core est.) | median page, 2 calls |
|---|---|---|---|
| 0.8b | 9.3s | ~18s | ~36s |
| 2b | 27s | ~54s | ~108s |
| 4b | 39.5s | ~79s | ~158s |

A live reader is not viable at 2b or 4b. **Pre-processing on upload (the deferred
§2 decision) becomes mandatory, not optional, if either is adopted.**

### Memory, against decision 1.2 (4 cores / 8 GB)

Resident = bge-m3 1.2 GB + chat model + ~4 GB OS/browser.

| model | weights | total | fits 8 GB? |
|---|---|---|---|
| 0.8b | 1.0 GB | ~6.2 GB | yes |
| 2b | 2.7 GB | ~7.9 GB | marginal |
| 4b | 3.4 GB | ~8.6 GB | **no** |

### Where this leaves the decision

- **4b gives the best detection (3/4) but does not fit the stated hardware.** A 4b
  choice is a decision to change decision 1.2, not a drop-in fix.
- **2b is the compromise**: doubles detection over 0.8b, fits at the margin, and
  costs ~3x the latency.
- **Neither reaches a level where flagging is safe yet.** Even 4b misses one of
  four, and flag precision stays at 33% on a 3-item sample.

**Prerequisite before any adoption:** the eval set needs ~10+ flag-positive units
and a rebalanced metric. Until then no model choice can be validated, only ranked.

---

## R-6 — Dedicated 77 MB MT model: translation quality fixed, verdicts not improved

**Status:** negative result, cleanly controlled
**Run:** 2026-08-14, `scripts/experiment_decompose.py`, same 6 cases as R-4

R-4 showed translation hurting, but confounded: the *chat model* did the translating
and mangled the content. This retest uses a purpose-built MT model to separate
"translation is a bad idea" from "the 0.8b model cannot translate".

### The translation problem is genuinely solved

`craftwise/ct2-opus-mt-fr-en-int8` — 77 MB on disk, CTranslate2 int8, **no PyTorch**
(38 MB runtime wheel). Fits the 300 MB budget with room to spare.

| source | qwen3.5:0.8b (R-4) | opus-mt (77 MB) |
|---|---|---|
| "des **éponges**" | "**sperm**" | "**sponges**" |
| "les **stérilets**" | "**sterilizers**" | "steriles" (minor) |
| "dont on parle **peu**" | "a **minor** aspect" | "which is little discussed" |

**83 ms per claim against ~7 s for the chat model.** A 74M-parameter task-specific
model beats an 800M general one at translation by a wide margin — the parameter
efficiency argument holds.

**Decoding gotcha worth keeping:** Marian via CTranslate2 requires an explicit
`</s>` appended to the source tokens. Without it the decoder has no end-of-source
marker and degenerates — "In 1791, by 1791, sponge sponges could be used as
contraceptive contraceptive." With it, the same input gives "In 1791 sponges could
be used as a contraceptive." Documented in `src/translate.py`.

### But better translation does not improve verdicts

| variant | pipeline | score (of 6) | calls |
|---|---|---|---|
| **A** | baseline 4-way, French | **3** | 6 |
| E | opus-mt + French prompt | 1 | 6 |
| F | opus-mt + binary gates | 3 | 11 |
| G | opus-mt + **matched English prompt** | 2 | 6 |

E was itself confounded — an English claim inside a French prompt with French
examples. G fixes that with a full English prompt, English few-shots and English
field labels (`prompts/classify_en.txt`). It is the fair test, and it still loses.

### What G actually changed: recall up, precision down

| | known-outdated (of 4) | controls (of 2) |
|---|---|---|
| A (French) | 1 | **2** |
| G (English) | **2** | **0** |

G detects more (adds the IUD-nidation claim) but fails both controls — including
labelling the 1791 sponges passage `outdated`, in direct violation of the history
rule. That is the dangerous direction: §9 weights false positives on `outdated`
above misses, and "textbook's history section is out of date" is precisely the
error that would discredit the tool in front of a teacher.

### Conclusion

Cross-lingual load was **not** a significant part of the failure. With translation
quality no longer a variable, the verdict task does not improve. This isolates the
cause further: the model reads the evidence incorrectly in either language.

Four software-side approaches are now measured and rejected — prompt engineering
(R-3), decomposition (R-4), chat-model translation (R-4), dedicated MT with a
matched prompt (R-6). Only model size moved the needle (R-5).

### Extended to 2b and 4b (2026-08-14)

Variant A comes from the R-5 bake-off; variant G re-run per model.

| model | A: French | G: opus-mt + English | A detection / controls | G detection / controls |
|---|---|---|---|---|
| 0.8b | **3/6** | 2/6 | 1/4 / 2/2 | 2/4 / 0/2 |
| 2b | **4/6** | **4/6** | 2/4 / 2/2 | 3/4 / 1/2 |
| 4b | **5/6** | 3/6 | 3/4 / 2/2 | 2/4 / 1/2 |

**Translation never wins.** It ties at 2b and loses at 0.8b and 4b — and the gap
widens with model size, the opposite of "bigger models use the English prompt
better".

At 2b the tie hides a trade: G detects one more claim and fails one more control.
Per §9 that is the wrong direction at equal score.

**These differences are mostly within noise.** At 2b, A catches `sti` + `iud` while
G catches `gynecomastia` + `sti` + `ovulation` — the error sets are partly
complementary rather than nested, which is the signature of randomness, not a
stable capability difference. With n=6 and a model that is not reproducible at
temperature 0 (R-3), only the 4b gap (5 vs 3) is plausibly real.

### One systematic effect, and a doubt about the label itself

`CONTROL def-contraception` fails under G for **all three** models (0.8b and 2b say
`attention`, 4b says `outdated`) while passing under A for all three. That is
systematic, not noise.

The claim: *"La contraception est l'ensemble des méthodes **réversibles** ayant pour
but d'empêcher une grossesse."* Labelled `okay`.

**That label may be wrong.** Sterilisation is contraception and is not reversible,
and the retrieved *Contraceptive Technology* entry lists sterilisation first. A
verdict of `attention` on an over-narrow definition is defensible — arguably more
correct than the ground truth. If so, G's scores rise by one across the board and
2b + opus-mt becomes the best configuration tested at 5/6.

This cannot be resolved by whoever wrote the label (R-2). **It needs an
independent domain reviewer**, and it is a concrete illustration of why the label set is the
binding constraint on every comparison in R-5 and R-6.

### Keep the artifact anyway

`src/translate.py` works, is fast, and costs 77 MB. It is the natural implementation
for the §5 display-language question if French evidence snippets are ever wanted,
and for translating rationales if an English-prompt pipeline is revisited on a
larger model.

---


## R-7 — mDeBERTa NLI: fast, deterministic, and no more accurate

> **Re-tested on the reviewed labels (R-10) and the core conclusion held:**
> contradiction probability still does not separate the classes — 25 of 25
> should-abstain units score at or above the weakest true flag. This was the
> failure most likely to have been an artefact of the broken benchmark, and it
> was not.

**Status:** complete. Not adopted, but the determinism and latency findings matter.
**Run:** 2026-08-14, `src/nli.py`, `scripts/calibrate_nli.py`, `scripts/eval.py --backend nli`

`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, quantised ONNX (339 MB),
run on `onnxruntime` (19 MB wheel) + `tokenizers`. **No PyTorch, no transformers, no
LLM in the path.** Sentence-level: each abstract sentence is scored against the claim
and aggregated by max, which lets the rationale quote the deciding sentence.

### Head to head

| engine | 6-case | 42-unit exact | flag precision | time (6 cases) | deterministic |
|---|---|---|---|---|---|
| qwen3.5:0.8b, French | 3/6 | 73.8–78.6% | 33–50% | 41 s | no |
| qwen3.5:2b, French | 4/6 | 69.0–71.4% | 17–20% | 94 s | no |
| qwen3.5:4b, French | **5/6** | 73.8–76.2% | 33% | 137 s | no |
| **mDeBERTa NLI, French** | 4/6 | 71.4% | 20% | **6 s** | **yes** |
| mDeBERTa NLI, opus-mt | 3/6 | — | — | 8 s | yes |
| *always-abstain* | — | *69.0%* | *0%* | — | — |

### What NLI wins outright

- **Determinism.** Three consecutive eval runs are byte-identical. Every generative
  configuration varies by up to ~5 points between identical runs (R-3) — larger than
  most differences under measurement here. This alone makes the §9
  edit→eval→compare loop trustworthy.
- **Speed.** 22 ms per premise/hypothesis pair at steady state; a full unit in
  ~0.5–2 s against 9–40 s generative. **The live reader becomes viable again**: a
  median page is ~2 units, so seconds rather than minutes.
- **Footprint.** bge-m3 1.2 GB + mDeBERTa 0.34 GB = **~1.5 GB**, against 2.2 GB for
  bge-m3 + qwen 0.8b. Lighter than what runs today, far inside the 8 GB target.
- **No hallucination surface.** The rationale quotes a real sentence and its score.

### Why it is still not the answer

Threshold calibration on the 42 labelled units found **no separation**:

| group | max contradiction probability |
|---|---|
| should flag | 0.087–0.093 |
| should be okay | 0.025–0.122 |
| **should abstain** | **0.036–0.188** |

Units that should abstain score *higher* for contradiction than genuine flags — 19 of
29 exceed the weakest true flag. Translating first makes it worse (25 of 29). No
threshold works: 0.05 catches 2/2 with 34/40 false flags; 0.10 catches 0/2.

So the 6-case 4/6 is substantially luck, and the 42-unit run confirms it: 71.4%
against a 69.0% always-abstain baseline, flag precision 20% (1 of 5), with four false
`attention` flags on correct statements.

### Why NLI fails here — a task-shape mismatch

1. **NLI contradiction is not factual outdatedness.** "70% of boys" and "prevalence
   varies from 4% to 69%" are not *logically* incompatible — both can sit in one
   discourse. NLI asks whether a hypothesis follows from a premise; the question here is
   whether a figure has been superseded. Measured: that pair scores contradiction
   **0.064** English-to-English.
2. **No arithmetic.** Catching the gynecomastia error needs 70 ∉ [4, 69]. NLI models
   do not compute.

Cross-lingual cost is real but secondary: the clearest contradiction scored 0.337
EN→EN and 0.201 EN→FR, so French costs ~40% of signal while preserving ordering.

### Conclusion

Six approaches measured: prompt engineering (R-3), decomposition (R-4), chat-model
translation (R-4), dedicated MT (R-6), larger models (R-5), NLI (R-7). **Only model
size improved detection**, and the best model does not fit the hardware.

NLI is worth remembering for two reasons independent of accuracy: it makes the eval
loop trustworthy, and it restores the live reader.

> **The implementation was removed on 2026-08-16.** `src/nli.py`,
> `scripts/calibrate_nli.py` and `scripts/fetch_nli_model.sh` are deleted, and
> `eval.py --backend nli` no longer exists. The hybrid this entry proposed — NLI
> as a cheap pre-filter — was ruled out in R-10: its contradiction scores do not
> separate the classes at all, so a pre-filter would forward nearly everything and
> save nothing. The findings below stand as a record; the code does not. Recover it
> from git history if the task shape ever changes.

---

## R-8 — The benchmark was wrong, not (only) the models

**Status:** invalidates parts of R-3 through R-7. Highest-priority correction.
**Found:** 2026-08-14, by re-reading the four "known-outdated" claims in full.

Six approaches all failed in the same narrow band (69–79% against a 69% baseline).
That pattern prompted a re-read of the claims themselves. **At least two of the four
are mislabelled, and a third was mis-targeted.**

### Claim-by-claim re-audit

| claim | recorded label | actually |
|---|---|---|
| `ovulation-28-days` | outdated/attention | **WRONG — the claim is correct** |
| `sti-antibiotics` | outdated | **mis-targeted** — right unit, wrong sentence |
| `gynecomastia-70pc` | outdated/attention | borderline; 70% sits at the top of a 4–69% reported range |
| `iud-nidation` | outdated/attention | fair, but the corpus lacks mechanism evidence — abstention was correct |

**`ovulation-28-days`.** Only the truncated first line was ever read. The full unit
says "tous les 28 jours **environ**" and then explicitly warns:

> « Chez la jeune fille, les cycles sont irréguliers, ce qui déplace cette période de
> fécondité de manière imprévisible : on ne peut donc pas s'en servir comme moyen de
> contraception fiable ! »

The textbook is correct and self-hedging. Every model that answered
`insufficient_evidence` was **right and was scored wrong**.

**`sti-antibiotics`.** The unit is three sentences. The genuinely outdated one is the
last — « **Le SIDA, lui, reste à ce jour mortel.** » — which ART has superseded. The
probe was built around the *antibiotics* clause instead, where "sauf le SIDA" is
actually correct. The best detection target in the whole corpus was never tested.

### Tested properly, the system works

« Le SIDA reste à ce jour mortel. » in isolation:

| input | retrieved | LLM | NLI |
|---|---|---|---|
| isolated sentence | *HIV Infection and AIDS in Sub-Saharan Africa* (0.449) | attention | **outdated** ✓ |
| merged 3-sentence unit | CDC STD guidelines (0.391) | insufficient_evidence | outdated |

NLI's extractive quote: *"The possibility of an AIDS free generation cannot be
realized unless…"* — correct verdict, relevant evidence, no LLM required.

### Two structural bugs this exposes

1. **Merge granularity destroys detection.** The 3-sentence unit retrieves a
   *different, worse* paper than the one sentence that matters, and the LLM then
   abstains. Paragraph-level units are right for topical retrieval and wrong for
   claim checking. Sentence-level units, or a second sentence-level pass over
   flagged paragraphs, is likely required.
2. **The floor blocks short high-value claims.** The isolated sentence scores 0.449,
   above `DEFAULT_FLOOR = 0.39`, so in production it never reaches a model.
   R-2 already measured that longer units embed *better* (85 words → 0.296, 9 words
   → 0.372); the floor was calibrated on "adjudicable" units, not on flag-positive
   ones, and short punchy claims are exactly the checkable ones. **The floor is
   selecting against detection.**

### What this invalidates

- **All accuracy figures in R-3, R-5, R-6, R-7 are unreliable.** They were measured
  against a benchmark whose positive class is largely mislabelled. "The model cannot
  comprehend" is overstated — models were frequently correct and scored wrong.
- **Relative rankings are probably still directionally valid** (same benchmark applied
  to every configuration), but the absolute verdict "verdict generation does not
  work" is not supported.
- **R-5's conclusion that only model size helps** needs re-testing once labels are fixed.

### What does NOT change

Model rationales were incoherent in ways labels cannot explain — a present-tense
claim about ovarian function described as "un fait historique et une expérience
ancienne". Real weakness exists; its magnitude is unknown.

### Required before any further model work

1. **Re-label from scratch**, by someone who reads the full unit — the `ovulation`
   error came from reading a truncated line.
2. **Re-target the positive set** on sentences, not paragraphs. Start with
   « Le SIDA reste à ce jour mortel. »
3. **Recalibrate the floor against flag-positive units**, not merely adjudicable ones.
4. **Re-run the R-5 bake-off** on the corrected benchmark.

Sequencing matters: further model comparison on the current labels measures the
labels, not the models.

---

## R-9 — The 42-unit label set audited: both flags defective; rebuilt as labels_v2

**Status:** implemented; labels provisional pending independent review
**Run:** 2026-08-16. Audit of every v1 label against full unit text;
`scripts/sweep_candidates.py`; `labels_v2.jsonl`; eval metrics rebuilt.

R-8 audited the four *probe* claims. This audit covered the 42-unit eval set
itself — the ground truth under every number in R-3 through R-7 — and found the
same disease in worse form.

### Both v1 flag-positive labels were wrong or contested

The entire flag precision/recall signal rested on 2 units:

| v1 flag | defect |
|---|---|
| `contraceptionSVT4:p3:p3l16` `attention` — "STI treatability has moved" | **Mis-targeted.** The unit is a correct list of STI pathogens; it says nothing about treatability. The sentence the note describes — « Le SIDA, lui, reste à ce jour mortel » — is in the neighbouring unit `p3l27`, which was never labelled. |
| `svt_manual4_puberte:p13:p13l33` `attention` — "28 jours idealises variability" | **Contested by the book itself.** A summary box using the standard idealisation; every other statement adds « environ », and `p11l10` explicitly warns cycles are unusable for contraception timing. |

Meanwhile the genuine positives were excluded or actively mislabelled:
`p3l27` (AIDS-fatal — the clearest outdated claim in the corpus) and `p3l32`
(gynecomastia 70%) were absent; `p7l0` (IUD-nidation) and `p14l44` (two-thirds
implantation failure) were labelled **non-adjudicable**, so a model flagging
them — the correct behaviour — was *penalised*.

### Root cause: "adjudicable" conflated two questions

v1's single axis mixed "is this a checkable claim" (a fact about the unit) with
"can the current corpus adjudicate it" (a fact about the system under test).
That baked corpus gaps into the ground truth: improve the corpus and the labels
silently become wrong, and any model smarter than the corpus scores as
hallucinating.

### What was built

1. **`labels_v2.jsonl`** (56 units): corpus-independent schema — `is_claim`,
   `in_scope`, `true_status` (okay/outdated/contested), `target_sentence` for
   positives (R-8's granularity finding), `needs_review`, and `v1` recording
   every disagreement with the old label. Positive class: **4 outdated + 7
   contested = 11 flag-eligible units** (v1 had 2), including a new find from
   the sweep: `p7l17` — IUDs « ne peut pas être utilisé chez les jeunes filles
   vierges », contradicted by WHO MEC / ACOG guidance on adolescent and
   nulliparous IUD use.
2. **`scripts/sweep_candidates.py`**: ranks all 683 units by flag-candidate
   signatures (numbers, absolutes, mechanism verbs; history markers penalised).
   Replaces distance-band sampling, which systematically under-sampled short
   assertive claims. 195 units carry signal; the labelled set came from its
   shortlist plus the v1 carry-over.
3. **Eval metrics rebuilt** (`scripts/eval.py`): exact match is gone (R-5:
   anti-correlated with detection). Headline is flag recall (on outdated) and
   flag precision (flags on outdated|contested); false-flag rate reported
   separately as §9's heaviest error. Contested units accept flag *or*
   abstention and stay out of the recall denominator. `--runs N` reports spread
   for non-reproducible generative backends. `compare()` made schema-agnostic.
4. **`scripts/known_claims.py` corrected**: probes now target `sida-mortel` and
   `iud-virgins`; `ovulation-28-days` kept as an explicit must-NOT-flag control.
5. **Review sheet** (local working document): the 14 `needs_review` labels with French originals,
   English translations, proposed labels, and the specific question a human
   reviewer must answer. **No number from labels_v2 should be published before
   that review.**

### First numbers on the corrected benchmark

Retrieval, floor 0.39: recall 74.2% (23/31 in-scope claims), noise leak 8.0%
(2/25 — both are the history controls). But the new floor check confirms R-8
quantitatively: **2 of the 4 outdated units (`p7l0` 0.444, `p1l18` 0.415) never
reach a model at floor 0.39.** The floor is capping flag recall at 50% before
any classifier runs.

Head to head at floor 0.39 (`--runs 3` for the generative backend):

| engine | flag recall (of 4) | flag precision | false-flag rate | acceptable |
|---|---|---|---|---|
| qwen3.5:0.8b, 3 runs | **25.0%** (stable) | 25–40% | 6.7% | 89.3% |
| mDeBERTa NLI | **50.0%** | 33.3% | 13.3% | 83.9% |
| *floor ceiling* | *50.0%* | — | — | — |

Only two outdated units clear the floor at all (`p3l27` sida-mortel, `p7l17`
iud-virgins). **NLI flags both; 0.8b flags only `iud-virgins`** and reads the
AIDS-fatal unit as `insufficient_evidence` — consistent with R-8's merge-
granularity finding, since the outdated sentence is the last of three. So on
the corrected benchmark NLI beats 0.8b on detection, at the cost of doubling
the false-flag rate (6 vs 3 false `attention`/`outdated` flags). NLI's misses
are **exactly the floor-blocked units**, which reads as "its recall problem is
the floor's fault, not the model's."

> **Corrected in R-10 — do not stop reading here.** That inference does not
> survive the threshold calibration. NLI's contradiction scores do not separate
> the classes at all, so it "catches" the units that reach it by flagging
> broadly rather than by discriminating. Raising the floor confirms this: recall
> goes to 100% and the false-flag rate goes to 31%. The LLM's misses are also
> not primarily floor-blocked — `p3l27` reaches it at both floors and is misread
> every time.

The corrected `known_claims --bypass-floor` probe agrees (0.8b): `iud-virgins`
caught, the `ovulation` control correctly left alone, `sida-mortel` /
`gynecomastia` / `iud-nidation` missed — 2/5. Note the nidation probe matches
the 13-word TOC line `p1l18` first, the hardest possible retrieval target.

### What this leaves open

- [x] Independent review of the flagged labels — done, see R-10
- [x] Recalibrate the floor with `blocked_flag_positives` as a gating metric — see R-10
- [ ] Re-run the R-5 bake-off (`--runs 3`) on labels_v2 at the chosen floor
- [ ] Sentence-level second pass for merged units (R-8 bug 1) remains unbuilt

---

## R-10 — Labels confirmed by second reader; the floor, not the model, was capping recall

**Status:** labels final; floor decision needs an owner
**Run:** 2026-08-16. Label review; `scripts/calibrate.py --sweep`
(ported to the v2 schema); `scripts/eval.py --full` at floors 0.39 and 0.45.

### Every proposed label survived external review

A second reader verified each of the 14 `needs_review` labels against current
sources. **No `true_status` changed.** The audit trail is kept as a local working document;
each label now carries `reviewed_by: second-reader-confirmed-2026-08-16`. This
retires the caveat carried since R-2 — that the labels were written without review
and could not support a published number.

Key confirmations: ACOG PB-186 and Ortiz & Croxatto (2007) on IUD mechanism
(fertilisation-prevention is primary, so `p7l0` is genuinely outdated); WHO MEC
Category 2 for IUDs from menarche to 20 and for nulliparity (`p7l17` confirmed
as the most consequential error in the chapter); U=U and ART life expectancy
(`p3l27`); Jarvis 2016/2020 putting natural pre-implantation loss at 10–40%
against the book's "two in three" (`p14l44`); Freeman 1907 as the true source of
the "Socrates" quote (`p4l31`).

Two refinements were folded into notes. On `p7l17`, the secondary claim "le plus
utilisé dans le monde" is wrong — female sterilisation leads worldwide (UN DESA
2019, ~219M users) — but "the IUD leads reversible methods" is measurement-
dependent and should not be asserted (male condoms, 189M, exceed IUDs, 159M, by
2019 user counts). On `p2l44`, the French-pedagogy defence of "méthodes
réversibles" fails: current French sources define contraception as "temporaire,
à long terme **ou définitive**", which strengthens rather than weakens the flag.

Judgment calls were closed conservatively: `p1l18` stays `outdated` but carries
`duplicate_of: p7l0`, and the eval now counts distinct claims — **3 outdated
claims across 4 units**, so a duplicate cannot inflate recall. `p2l44`,
`p14l44`, `p7l24`, `p3l2`, `p3l46`, `p4l31` stay `contested`; `p7l5` stays
`okay` with the emphasis-inversion recorded; `p7l24`'s flaggable component is
sub-claim (b), the "3 days" window, since (c) is G-1 framing and out of v1 scope.

### The floor gate: a hard trade, not a free win

`calibrate.py --sweep` now gates on admitting every **in-scope** flag-positive
unit (out-of-scope ones must be blocked, so they are excluded — an early version
of the gate chased the out-of-scope Socrates unit to a nonsense floor of 0.50).

| floor | in-scope claims kept | noise leak | flag-positives blocked |
|---|---|---|---|
| 0.39 (current) | 23/31 | 2/25 | **2/10** |
| 0.42 | 28/31 | 6/25 | 1/10 |
| **0.45 (gate-passing)** | 30/31 | **10/25** | **0/10** |

Measured on both backends (NLI deterministic; qwen3.5:0.8b over 3 runs):

| engine | floor | flag recall (of 3) | flag precision | false-flag rate |
|---|---|---|---|---|
| NLI | 0.39 | 50.0% | 33.3% | 13.3% |
| NLI | 0.45 | **100.0%** | 26.3% | **31.1%** |
| qwen3.5:0.8b | 0.39 | 33.3% | 25–40% | 6.7% |
| qwen3.5:0.8b | 0.45 | **33.3%** | 14–25% | **13.3%** |

**Raising the floor helps NLI and does nothing whatever for the LLM.** qwen
catches the same single claim (`p7l17`, IUD-virginity) at both floors while its
false-flag rate doubles. The two claims it misses are not floor-blocked in the
way that matters: `p3l27` (sida-mortel) passes the floor at 0.388 and reaches the
model at *both* settings, and is misread as `insufficient_evidence` every time —
consistent with R-8's merge-granularity bug, since the outdated sentence is the
last of three in that unit.

So the R-8 hypothesis holds only for NLI. **For the generative path the floor was
never the ceiling; comprehension is.** And NLI's gain is not what it appears —
see the correction below.

**Floor recommendation: keep 0.39.** Raising it is strictly worse for the LLM
(no recall gained, 2x false flags) and buys NLI recall only through
indiscriminate flagging. `DEFAULT_FLOOR` is unchanged; the trade is recorded in
`config.py` so the next person does not re-derive it.

This is the same wall as R-7, relocated: distance cannot separate flag-positive
from noise, because the two genuinely outdated short claims (`p7l0` 0.444,
`p1l18` 0.415) sit inside the noise band (25 non-claims spread 0.334–0.581).
**No floor exists that admits them while excluding the noise.** The fix has to
be a guard or a second pass, not a threshold.

### Correction: NLI's 100% recall is not discrimination

Read alone, "NLI catches every outdated claim at floor 0.45" looks like
capability. `calibrate_nli.py` on the corrected labels shows it is not.
Contradiction probability by expected label:

| group | n | min | median | max |
|---|---|---|---|---|
| should flag | 10 | 0.025 | 0.095 | 0.186 |
| should be okay | 21 | 0.029 | 0.087 | 0.149 |
| should abstain | 25 | 0.036 | **0.107** | 0.188 |

The units that should abstain have the **highest** median contradiction score of
the three groups, and **25 of 25 score at or above the weakest true flag.** The
distributions are not merely overlapping, they are indistinguishable. NLI reaches
100% recall by flagging widely enough to sweep the positives up with everything
else, which is exactly what the 31% false-flag rate records.

**This is the most important result of the relabel, because it is the one that
did not change.** R-7 concluded NLI contradiction is not a usable signal here,
and the leading hypothesis (R-8) was that the broken benchmark caused it. It did
not: with a reviewed label set and a positive class five times larger, the
separation is still absent. R-7's mechanism explanation stands — NLI asks whether
a hypothesis follows from a premise, while the product asks whether a figure has
been superseded, and no amount of relabelling makes those the same question.

Corollary for the hybrid idea floated in R-7 and R-9: **an NLI pre-filter is dead
on this evidence.** A pre-filter must be cheap *and* discriminative; this one
admits 40 of 46 negatives at the threshold that catches 8 of 10 positives, so it
would forward nearly everything and save nothing.
