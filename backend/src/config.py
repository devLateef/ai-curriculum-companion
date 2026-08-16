"""Central configuration.

Retargeting the corpus -- adding a subject, widening the year range, changing the
models -- should be an edit to this file alone. No other module hardcodes a
subject, a field id, or a threshold.
"""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "lancedb"
TABLE_NAME = "works"

# --- Corpus scope -----------------------------------------------------------
# Search terms are derived from the claims the corpus must adjudicate, not from
# the field they belong to. Sampling a field by citation count returns whatever
# is most cited in that field, which is rarely the literature that addresses any
# particular textbook claim; measured against ten known-outdated claims, that
# approach produced usable evidence for one.
SEEDS_REPRODUCTIVE_HEALTH = [
    # Contraception
    "long-acting reversible contraception",
    "emergency contraception effectiveness",
    "contraceptive effectiveness typical use failure rate",
    "combined oral contraceptive contraindications",
    "contraceptive implant intrauterine device adolescents",
    "condom effectiveness sexually transmitted infection",
    "family planning access sub-Saharan Africa",
    "unmet need for contraception low income countries",
    "contraceptive counselling adolescents",
    # STI / HIV
    "pre-exposure prophylaxis HIV prevention",
    "undetectable untransmittable viral suppression",
    "HPV vaccination adolescent",
    "HIV prevention adolescents sub-Saharan Africa",
    "sexually transmitted infection burden adolescents",
    # Puberty
    "puberty onset secular trend",
    "precocious puberty incidence",
    "adolescent growth spurt timing",
    "gynecomastia adolescent prevalence",
    "age at menarche trend",
    # Reproduction
    "age-related fertility decline",
    "menstrual cycle variability ovulation timing",
    "adolescent pregnancy outcomes",
    "maternal mortality adolescent pregnancy",
    # Sex education
    "comprehensive sexuality education effectiveness",
    "abstinence-only education outcomes",
]

# Field ids verified against https://api.openalex.org/fields
#   fields/11  Agricultural and Biological Sciences
#   fields/13  Biochemistry, Genetics and Molecular Biology
#   fields/32  Psychology
#
# mode="seeds"  -> claim-first search, used by the active subject
# mode="fields" -> broad field sampling, retained only for pre-existing rows
SUBJECTS: dict[str, dict] = {
    "reproductive_health": {
        "mode": "seeds",
        "seeds": SEEDS_REPRODUCTIVE_HEALTH,
        "per_seed": 10,
    },
    "biology": {
        "mode": "fields",
        "fields": ["fields/11", "fields/13"],
        "target": 100,
    },
    "psychology": {
        "mode": "fields",
        "fields": ["fields/32"],
        "target": 100,
    },
}

# Other subjects remain in the table but are outside the evaluated scope.
PRIMARY_SUBJECT = "reproductive_health"

# Applies to field mode only. Restricting seeded searches to reviews collapses
# them -- "long-acting reversible contraception" returns 2024 works unfiltered
# and 47 with type:review -- and the works that refute a specific claim are
# usually primary studies or guidelines rather than reviews.
WORK_TYPE = "review"
YEARS = list(range(2018, 2026))

# Seed mode reaches further back than field mode: a definitive 2015 trial still
# refutes a claim from a 1990s textbook.
SEED_YEAR_MIN = 2014

LANGUAGE = "en"

# Below this length an abstract is almost always boilerplate or a truncation
# artifact rather than real content.
MIN_ABSTRACT_CHARS = 200

# --- Embedding --------------------------------------------------------------
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")
EMBED_DIM = 1024
EMBED_BATCH = 32

# --- Generation -------------------------------------------------------------
# Fixed by the 4-core / 8 GB target. The embedding model (~1.2 GB) plus this
# (~1 GB) plus the runtime leaves little headroom, so a larger model is not an
# available fix for output quality; that has to come from the corpus, the
# prompt, or the guards.
CHAT_MODEL = os.getenv("CHAT_MODEL", "qwen3.5:0.8b")

# A larger context buys nothing at this prompt size and costs KV cache.
NUM_CTX = 4096

# --- Retrieval --------------------------------------------------------------
# The floor is the distance above which retrieved evidence is discarded and the
# unit is left unjudged. It is the main precision control: kNN always returns
# results, so without it a claim the corpus knows nothing about still comes back
# with the least-distant abstracts.
#
# Derived by `scripts/calibrate.py --sweep` against the hand-labelled units.
# Measured trade at three candidate values:
#
#   floor      claims kept    noise admitted    flag-positives blocked
#   0.39          23/31            2/25                  2/10
#   0.42          28/31            6/25                  1/10
#   0.45          30/31           10/25                  0/10
#
# 0.45 admits every flag-positive unit and was still rejected: it doubles the
# false-flag rate while the generative model gains no detection at all, because
# the claims it misses are ones it reads and misjudges rather than ones the
# floor withheld.
#
# Re-run `scripts.measure` then `scripts.calibrate --sweep` after any change to
# SUBJECTS, the seed list, or EMBED_MODEL.
DEFAULT_FLOOR = 0.39
DEFAULT_K = 5
CANDIDATE_POOL = 20

# Prefilter applied when a request omits `subject`. One subject is in scope, so
# this is a configured default rather than an inference. Set to None to search
# the whole table.
DEFAULT_SUBJECT = os.getenv("DEFAULT_SUBJECT", "reproductive_health")

# --- OpenAlex ---------------------------------------------------------------
OPENALEX_BASE = "https://api.openalex.org/works"

# The polite pool. Without a real address OpenAlex throttles or blocks requests.
MAILTO = os.getenv("OPENALEX_MAILTO", "")
