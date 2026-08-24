"""
Evidence validator. This is the component that actually delivers the
product's core promise: a claim is only shown as "verified" if its cited
chunk_ids (a) exist and (b) plausibly support the claim text.

Deliberately simple for MVP: lexical overlap is a heuristic, not a proof of
correctness, and that's fine — the point is to catch obviously invalid or
hallucinated citations (nonexistent chunk_ids, zero-overlap claims), not to
build a research-grade entailment model in an 8-hour project. This
limitation should be stated plainly in the README, not hidden.
"""

import re
from typing import Dict, List

from app.models import Chunk, Claim

MIN_CONFIDENCE_TO_VALIDATE = 0.08
STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is",
    "are", "was", "were", "be", "this", "that", "with", "as", "by", "it",
    "its", "at", "from", "which", "has", "have", "had",
}


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-Z']+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def _overlap_score(claim_text: str, chunk_texts: List[str]) -> float:
    claim_tokens = _tokenize(claim_text)
    if not claim_tokens:
        return 0.0
    chunk_tokens = set()
    for t in chunk_texts:
        chunk_tokens |= _tokenize(t)
    if not chunk_tokens:
        return 0.0
    overlap = claim_tokens & chunk_tokens
    return len(overlap) / len(claim_tokens)


def build_validated_claims(
    raw_claims: List[dict], chunk_lookup: Dict[str, Chunk]
) -> List[Claim]:
    """
    raw_claims: list of {"text": str, "chunk_ids": [str, ...]} from the LLM.
    chunk_lookup: chunk_id -> Chunk, built from the actual chunks sent to the model.

    Never trusts page numbers from the LLM — they are resolved here, from
    chunk_lookup, which is built from real extracted document metadata.
    """
    validated: List[Claim] = []
    for i, raw in enumerate(raw_claims):
        text = raw.get("text", "").strip()
        chunk_ids = raw.get("chunk_ids", []) or []
        if not text:
            continue

        # Drop chunk_ids that don't actually exist -- this is the step that
        # prevents outright hallucinated citations from ever reaching the UI.
        existing_ids = [cid for cid in chunk_ids if cid in chunk_lookup]
        page_numbers = sorted({chunk_lookup[cid].page_number for cid in existing_ids})
        chunk_texts = [chunk_lookup[cid].text for cid in existing_ids]

        confidence = _overlap_score(text, chunk_texts) if chunk_texts else 0.0
        is_validated = bool(existing_ids) and confidence >= MIN_CONFIDENCE_TO_VALIDATE

        validated.append(
            Claim(
                id=f"claim{i+1}",
                text=text,
                chunk_ids=existing_ids,
                page_numbers=page_numbers,
                validated=is_validated,
                confidence=round(confidence, 3),
            )
        )
    return validated
