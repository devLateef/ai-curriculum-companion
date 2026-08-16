"""Offline French->English translation with a dedicated MT model.

Why a separate model rather than the chat model: an earlier experiment had
qwen3.5:0.8b translate the claim itself and it mangled the content -- "des eponges"
(sponges) became "sperm", "sterilets" (IUDs) became "sterilizers". Feeding that to
the classifier made results worse, not better.

opus-mt-fr-en is ~74M parameters against 800M, and is trained for exactly one task.
Quantised to int8 and run through CTranslate2 it occupies ~77 MB on disk and needs
no PyTorch -- the runtime is a 38 MB wheel. That matters against the 8 GB target:

    bge-m3 1.2 GB + qwen 0.8b 1.0 GB + MT 0.08 GB + OS/browser ~4 GB = ~6.3 GB

which fits, where qwen3.5:4b alone (~8.6 GB total) does not.
"""

import re
from functools import lru_cache
from pathlib import Path

from . import config

MODEL_DIR = config.BACKEND_DIR / "models" / "opus-mt-fr-en"

# Marian models are trained on single sentences and degrade on long inputs, so
# split first and translate sentence by sentence.
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
MAX_CHARS = 400


class TranslationUnavailable(RuntimeError):
    pass


@lru_cache(maxsize=1)
def _engine():
    """Load once per process. Raises rather than silently degrading."""
    if not (MODEL_DIR / "model.bin").exists():
        raise TranslationUnavailable(
            f"No MT model at {MODEL_DIR}. See scripts/fetch_mt_model.sh."
        )
    try:
        import ctranslate2
        import sentencepiece as spm
    except ImportError as exc:  # pragma: no cover
        raise TranslationUnavailable(f"ctranslate2/sentencepiece missing: {exc}") from exc

    translator = ctranslate2.Translator(str(MODEL_DIR), device="cpu", compute_type="int8")
    src = spm.SentencePieceProcessor(str(MODEL_DIR / "source.spm"))
    tgt = spm.SentencePieceProcessor(str(MODEL_DIR / "target.spm"))
    return translator, src, tgt


def _chunks(text: str) -> list[str]:
    out: list[str] = []
    for sentence in SENTENCE_SPLIT.split(text.strip()):
        sentence = sentence.strip()
        if not sentence:
            continue
        # Hard-wrap anything still oversized, on whitespace.
        while len(sentence) > MAX_CHARS:
            cut = sentence.rfind(" ", 0, MAX_CHARS) or MAX_CHARS
            out.append(sentence[:cut])
            sentence = sentence[cut:].strip()
        out.append(sentence)
    return out


def translate(texts: list[str]) -> list[str]:
    """French -> English, one output per input. Sentences are batched together."""
    if not texts:
        return []
    translator, src, tgt = _engine()

    # Flatten every sentence of every input into one batch, then reassemble.
    flat: list[str] = []
    spans: list[tuple[int, int]] = []
    for text in texts:
        pieces = _chunks(text)
        spans.append((len(flat), len(flat) + len(pieces)))
        flat.extend(pieces)
    if not flat:
        return ["" for _ in texts]

    # The trailing </s> is mandatory, not cosmetic. Without it the decoder has no
    # end-of-source marker and degenerates into repetition: "Intrauterine
    # (sterilelet)" repeated four times, "In 1791, by 1791, sponge sponges...".
    # With it, the same input yields "In 1791 sponges could be used as a
    # contraceptive."
    tokens = [src.encode(s, out_type=str) + ["</s>"] for s in flat]
    results = translator.translate_batch(
        tokens,
        max_batch_size=16,
        beam_size=4,
        no_repeat_ngram_size=3,
        max_decoding_length=512,
    )
    english = [tgt.decode(r.hypotheses[0]) for r in results]
    return [" ".join(english[a:b]).strip() for a, b in spans]


def translate_one(text: str) -> str:
    return translate([text])[0]
