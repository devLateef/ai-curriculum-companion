"""Request and response models for the page-analysis contract.

Each incoming item is opaque except for `text` and `id`. Every other field is
echoed back unmodified, so a client can change its extraction schema without the
backend caring.

Geometry is a special case: it is read opportunistically when present, because
merging uses vertical gaps and font-size changes to find block boundaries, and
degrades to punctuation-only without it. Passthrough means echoing fields back
untouched, not refusing to look at them.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["okay", "attention", "outdated", "insufficient_evidence"]


class Item(BaseModel):
    """One text item as extracted client-side (a pdf.js text run, or a PDF line)."""

    model_config = ConfigDict(extra="allow")  # passthrough fields survive

    id: str
    text: str
    # [x, y, width, height] in PDF points. Height doubles as a font-size proxy.
    location: list[float] | None = None


class PageRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    doc_id: str
    page: int
    lang: str = "fr"
    subject: str | None = None
    # Publication year of the source document. Drives the guard that stops
    # evidence older than the textbook justifying an `outdated` verdict.
    doc_year: int | None = None
    items: list[Item]


class Ref(BaseModel):
    """A supporting work. Metadata only -- no snippet, per decision 1.5."""

    title: str
    doi: str | None = None
    year: int | None = None
    license: str | None = None
    source_url: str | None = None


class ItemVerdict(BaseModel):
    """One verdict per original item, including silent and skipped ones.

    `status` is present on every item; the client must never infer meaning from
    absence.
    """

    model_config = ConfigDict(extra="allow")

    id: str
    text: str
    status: Status
    rationale: str | None = None
    ref: list[Ref] = Field(default_factory=list)
