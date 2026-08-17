"""PDF upload route.

Accepts a PDF as multipart form data and runs the pdfplumber/spaCy extraction
pipeline over it. Kept as a separate blueprint from the JSON analysis routes:
the two take different input, use different evidence, and evolved separately.
Both are registered on one Flask app so CORS, logging and error handling are
configured once.

The processor loads a spaCy model, so it is constructed once at import rather
than per request.
"""

from flask import Blueprint, request

from ..core import config
from services.pdf_processor import PdfProcessor

bp = Blueprint("process", __name__)

processor = PdfProcessor()


@bp.post("/process")
def process():
    uploaded_pdf = request.files.get("file")
    if uploaded_pdf is None:
        return {"error": "no file uploaded; send a PDF as multipart field 'file'"}, 400

    pdf_data = processor.pdf_to_text(uploaded_pdf)
    info = processor.extract_information(pdf_data["text"])

    recent_sources: dict = {}
    comparison: dict = {
        "outdated_claims": [],
        "unverified_facts": [],
        "missing_recent_topics": [],
    }
    if config.ENABLE_ONLINE_SOURCES:
        recent_sources = processor.search_all_sources(info)
        comparison = processor.compare_with_recent_research(info)

    return {
        "pdf_summary": pdf_data,
        "curriculum_info": info,
        "recent_sources": recent_sources,
        "comparison": comparison,
        "online_sources_enabled": config.ENABLE_ONLINE_SOURCES,
    }
