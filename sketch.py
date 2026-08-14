from flask import request
from backend.services.pdf_processor import PdfProcessor
processor = PdfProcessor()

def process():
    # 1. extract PDF text
    uploaded_pdf = request.files.get("file")
    pdf_data = processor.pdf_to_text(uploaded_pdf)
    pdf_text = pdf_data["text"]

    # 2. extract curriculum info
    info = processor.extract_information(pdf_text)

    # 3. search recent sources
    recent_sources = processor.search_all_sources("machine learning")

    # 4. compare
    comparison = processor.compare_with_recent_research(info)

    result = {
        "pdf_summary": pdf_data,
        "curriculum_info": info,
        "recent_sources": recent_sources,
        "comparison": comparison
    }

    return result