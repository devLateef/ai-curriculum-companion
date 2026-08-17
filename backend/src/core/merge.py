"""Merge PDF text items into claim-sized units, then drop what is not a claim.

Replaces the LLM extraction call that earlier designs put at the head of the
pipeline. Extraction was the shakiest stage at small model
sizes and cost a call per page; these rules are deterministic, free, and testable
in isolation.

A PDF text item is not a claim. Extractors emit lines that break mid-sentence,
split columns, and carry running headers. Embedding "La memoire de travail a" and
"une capacite de sept elements" separately produces two useless vectors.
"""

import re
from dataclasses import dataclass, field
from statistics import median

from .schema import Item

# --- merge tuning ------------------------------------------------------------
# A line whose height differs from the run by more than this is a different
# style -- heading vs body -- and therefore a new block. Measured on the source
# PDFs: headings run ~18pt against ~10pt body.
HEIGHT_CHANGE_RATIO = 0.30
# Vertical gap beyond this multiple of line height starts a new block.
GAP_LINE_MULTIPLE = 1.8

TERMINAL = re.compile(r"[.!?][\"'”»)\]]*\s*$")

# A unit whose type is this much larger than the page's body size is a title.
HEADING_HEIGHT_RATIO = 1.25

# Trailing picture credits sit inside caption prose ("... chez les filles.
# Document RR."). Strip the credit rather than dropping the caption: on these
# pages captions carry real claims, not just labels.
CREDIT_TAIL = re.compile(
    r"\s*(document|doc|photos?|source|illustration|cliche|cliché)\b[^.]{0,60}\.?\s*$",
    re.I,
)

# Apple Pages exports paragraph markers as standalone glyphs in the text flow.
LEADING_MARKER = re.compile(r'^[\s"#!*••]+')

# --- prefilter ---------------------------------------------------------------
MIN_WORDS = 8

# Caption, credit and apparatus markers. These sit inside the body text flow in
# the source documents, so they cannot be excluded by geometry alone.
NOISE_PREFIXES = (
    "doc ", "doc.", "document ", "photo", "source:", "source :", "cf ", "cf.",
    "fig ", "fig.", "figure ", "schema ", "schéma ", "voir ",
)
NOISE_PATTERNS = [
    re.compile(r"^\s*(chapitre|chapter)\s+\d+", re.I),
    re.compile(r"^\s*(exercice|exercices|questions?|glossaire|sommaire|bilan)\b", re.I),
    re.compile(r"^\s*page\s*\d+\s*$", re.I),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"wikimedia|flickr|creative commons", re.I),
]


@dataclass
class Unit:
    """A merged, claim-sized span of text and the item ids it came from."""

    text: str
    source_ids: list[str] = field(default_factory=list)
    dropped_reason: str | None = None
    # Median type height of the items merged in; the font-size proxy.
    height: float | None = None

    @property
    def kept(self) -> bool:
        return self.dropped_reason is None


def _geom(item: Item) -> tuple[float, float, float, float] | None:
    loc = item.location
    if not loc or len(loc) < 4:
        return None
    x, y, w, h = loc[0], loc[1], loc[2], loc[3]
    return x, y, w, h


def _starts_new_block(prev: Item, cur: Item) -> bool:
    """Geometry-based block break. False when either item lacks a location."""
    pg, cg = _geom(prev), _geom(cur)
    if pg is None or cg is None:
        return False
    px, py, _, ph = pg
    cx, cy, _, ch = cg

    # Different type size => different role on the page.
    if ph > 0 and abs(ch - ph) / ph > HEIGHT_CHANGE_RATIO:
        return True

    # Moved up the page by more than a line => new column or new block. Text flows
    # downward, so any real upward jump ends the run. Direction of the horizontal
    # move is irrelevant: reading order goes left column -> right column, so a
    # column jump moves x *right*, not left.
    if cy < py - ph:
        return True

    # Large vertical gap => new block.
    if ph > 0 and (cy - py) > GAP_LINE_MULTIPLE * ph:
        return True

    return False


def merge_items(items: list[Item]) -> list[Unit]:
    """Join consecutive items into sentence-level units.

    Closes a unit on terminal punctuation, or on a geometric block break. Units
    carry every id they consumed so a verdict can be expanded back across the
    original geometry for highlighting.
    """
    units: list[Unit] = []
    buf_text: list[str] = []
    buf_ids: list[str] = []
    buf_h: list[float] = []
    prev: Item | None = None

    def flush() -> None:
        nonlocal buf_text, buf_ids, buf_h
        if buf_ids:
            text = " ".join(" ".join(buf_text).split())
            text = LEADING_MARKER.sub("", text)
            text = CREDIT_TAIL.sub("", text).strip()
            units.append(
                Unit(
                    text=text,
                    source_ids=list(buf_ids),
                    height=median(buf_h) if buf_h else None,
                )
            )
        buf_text, buf_ids, buf_h = [], [], []

    for item in items:
        text = item.text.strip()
        if not text:
            # Still record the id so every input gets a verdict.
            units.append(Unit(text="", source_ids=[item.id], dropped_reason="empty"))
            continue

        if prev is not None and _starts_new_block(prev, item):
            flush()

        buf_text.append(text)
        buf_ids.append(item.id)
        geom = _geom(item)
        if geom:
            buf_h.append(geom[3])
        prev = item

        if TERMINAL.search(text):
            flush()
            prev = None

    flush()
    return units


def _looks_like_noise(text: str) -> str | None:
    """Return a drop reason, or None to keep."""
    stripped = text.strip()
    low = stripped.lower()

    if not stripped:
        return "empty"
    for pat in NOISE_PATTERNS:
        if pat.search(stripped):
            return "apparatus"
    if low.startswith(NOISE_PREFIXES):
        return "caption"

    words = stripped.split()
    if len(words) < MIN_WORDS:
        return "too_short"

    # Axis labels, tables and formulas: mostly digits and symbols. Real prose in
    # French runs far above this.
    letters = sum(c.isalpha() for c in stripped)
    if letters / max(len(stripped), 1) < 0.55:
        return "non_prose"

    # Headings are short, title-styled and unpunctuated. Length alone already
    # caught most; this catches long all-caps banners.
    if stripped.isupper():
        return "heading"

    return None


def prefilter(units: list[Unit], body_height: float | None = None) -> list[Unit]:
    """Mark units that are not checkable claims. Nothing is discarded.

    Dropped units keep their ids because every original item must receive a
    verdict. On this hardware the prefilter is also a
    performance component: each unit it removes saves a 3-8s model call.

    Type larger than the page body is a title. Type *smaller* than body is a
    caption, and those are deliberately KEPT -- a documented deviation from
    dropped. On the source pages captions carry real claims ("cette croissance
    plus rapide se produit en premier lieu chez les filles"), so blanket-dropping
    them discards checkable content. Credit tails are stripped during merge instead.
    """
    for unit in units:
        if unit.dropped_reason is not None:
            continue
        if (
            body_height
            and unit.height
            and unit.height > body_height * HEADING_HEIGHT_RATIO
        ):
            unit.dropped_reason = "heading"
            continue
        unit.dropped_reason = _looks_like_noise(unit.text)
    return units


def page_body_height(items: list[Item]) -> float | None:
    """Median line height for the page: the reference for 'normal' body type."""
    heights = [g[3] for g in (_geom(i) for i in items) if g]
    return median(heights) if heights else None


def build_units(items: list[Item]) -> list[Unit]:
    """merge + prefilter, the whole deterministic front half."""
    return prefilter(merge_items(items), page_body_height(items))
