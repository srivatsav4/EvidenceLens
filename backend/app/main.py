"""
FastAPI application. Three endpoints, as specified in Phase 7:
  POST /api/upload            - validate + extract, return quick feedback
  POST /api/summarize/{doc_id} - run the full pipeline, return SummaryResult
  GET  /api/health            - trivial liveness check

No database: extracted pages/chunks for a document are held in an in-memory
dict for the lifetime of the process. This is a deliberate MVP choice (see
Phase 8) -- acceptable because the brief describes a single-session tool,
not a multi-user persistent app. If the process restarts (e.g. HF Space
cold start after 48h idle), in-flight document_ids are lost -- the frontend
handles this by treating a 404 on /summarize as "please re-upload."
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.chunker import build_chunks
from app.extractor import ExtractionError, extract_image, extract_pdf
from app.models import Chunk, Claim, Page, SummaryResult, UploadResponse
from app.summarizer import SummarizationError, generate_raw_claims
from app.validator import build_validated_claims

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB — stated limit, enforced up front
ALLOWED_PDF_TYPES = {"application/pdf"}
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/jpg"}

app = FastAPI(title="EvidenceLens API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store: document_id -> {"pages": [...], "chunks": [...], "filename": str}
_DOCUMENTS: Dict[str, dict] = {}

# very simple in-memory rate limiter: ip -> request count this minute would be
# a nice-to-have; for MVP within the 8-hour budget this is left as a documented
# known limitation rather than built out. See README "Known Limitations".


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large. Max size is 15 MB.")

    content_type = file.content_type
    if content_type in ALLOWED_PDF_TYPES:
        file_type = "pdf"
    elif content_type in ALLOWED_IMAGE_TYPES:
        file_type = "image"
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{content_type}'. Please upload a PDF, PNG, or JPG.",
        )

    try:
        if file_type == "pdf":
            pages: List[Page] = extract_pdf(contents)
        else:
            pages = extract_image(contents)
    except ExtractionError as e:
        raise HTTPException(status_code=422, detail=str(e))

    chunks = build_chunks(pages)
    document_id = str(uuid.uuid4())
    _DOCUMENTS[document_id] = {
        "pages": pages,
        "chunks": chunks,
        "filename": file.filename,
        "file_type": file_type,
    }

    warning = None
    if any(p.source == "ocr" for p in pages):
        warning = "This document was processed with OCR — extracted text may contain errors."

    return UploadResponse(
        document_id=document_id,
        filename=file.filename,
        file_type=file_type,
        page_count=len(pages),
        warning=warning,
    )


@app.post("/api/summarize/{document_id}", response_model=SummaryResult)
def summarize_document(document_id: str):
    doc = _DOCUMENTS.get(document_id)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found (it may have expired after a server restart). Please re-upload.",
        )

    chunks: List[Chunk] = doc["chunks"]
    chunk_lookup = {c.id: c for c in chunks}

    try:
        raw, was_truncated = generate_raw_claims(chunks)
    except SummarizationError:
        raise HTTPException(
            status_code=503,
            detail="Summarization is temporarily unavailable (the AI service may be rate-limited). Please try again shortly.",
        )

    def to_claims(key: str) -> List[Claim]:
        return build_validated_claims(raw.get(key, []), chunk_lookup)

    return SummaryResult(
        document_id=document_id,
        summary_short=to_claims("short"),
        summary_medium=to_claims("medium"),
        summary_long=to_claims("long"),
        chunks=chunks,
        llm_degraded=was_truncated,
    )


# Serve the built React frontend, if present (populated by the Docker build).
_FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
