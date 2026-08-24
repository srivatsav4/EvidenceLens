"""
Extraction layer. This is the component that makes the whole provenance
story possible: every extracted page keeps its page_number attached from
the very first step, so nothing downstream ever has to *guess* where text
came from.

Two paths:
  - PDF  -> PyMuPDF, native per-page text extraction
  - Image -> Tesseract OCR, treated as a single page

Both paths raise ExtractionError on failure so the API layer can turn that
into a clean, user-facing message instead of a stack trace.
"""

from typing import List
import io

import fitz  # PyMuPDF
import pytesseract
from PIL import Image

from app.models import Page

MIN_OCR_CHARS = 20  # below this, treat OCR output as too unreliable to summarize


class ExtractionError(Exception):
    pass


def extract_pdf(file_bytes: bytes) -> List[Page]:
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
    except Exception as e:
        raise ExtractionError(f"Could not read this PDF ({e}). It may be corrupted or encrypted.")

    if doc.page_count == 0:
        raise ExtractionError("This PDF has no pages.")

    pages: List[Page] = []
    total_chars = 0
    for i, page in enumerate(doc, start=1):
        text = page.get_text("text").strip()
        total_chars += len(text)
        pages.append(Page(page_number=i, raw_text=text, source="native_text"))
    doc.close()

    if total_chars < MIN_OCR_CHARS:
        raise ExtractionError(
            "This PDF appears to contain no extractable text (it may be a scanned "
            "image saved as PDF). Try uploading it as an image instead, or a PDF with "
            "selectable text."
        )

    return pages


def extract_image(file_bytes: bytes) -> List[Page]:
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()
    except Exception as e:
        raise ExtractionError(f"Could not read this image ({e}).")

    try:
        text = pytesseract.image_to_string(image).strip()
    except Exception as e:
        raise ExtractionError(f"OCR failed on this image ({e}).")

    if len(text) < MIN_OCR_CHARS:
        raise ExtractionError(
            "OCR could not extract meaningful text from this image. The scan quality "
            "may be too low, or the image may not contain readable text."
        )

    return [Page(page_number=1, raw_text=text, source="ocr")]
