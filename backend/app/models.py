"""
Pydantic schemas — this is the data model defined in Phase 8 of the
architecture doc. Keep this file as the single source of truth for the
backend<->frontend contract; every endpoint response should be built from
these models so the frontend never has to guess the shape of the data.
"""

from typing import List, Literal, Optional
from pydantic import BaseModel


class Page(BaseModel):
    page_number: int
    raw_text: str
    source: Literal["native_text", "ocr"]


class Chunk(BaseModel):
    id: str
    page_number: int
    text: str


class Claim(BaseModel):
    id: str
    text: str
    chunk_ids: List[str]
    page_numbers: List[int]
    validated: bool
    confidence: float


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    file_type: Literal["pdf", "image"]
    page_count: int
    warning: Optional[str] = None  # e.g. low-quality OCR warning


class SummaryResult(BaseModel):
    document_id: str
    summary_short: List[Claim]
    summary_medium: List[Claim]
    summary_long: List[Claim]
    chunks: List[Chunk]
    llm_degraded: bool = False  # true if we fell back to plain summary (no claim-linking)


class ErrorResponse(BaseModel):
    detail: str
