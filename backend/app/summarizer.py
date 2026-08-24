"""
Summary generation via Groq. This is the piece implementing the Phase 9 AI
design: the LLM is only ever allowed to say *which chunk_ids* a claim came
from. It never states a page number itself — page numbers are resolved
deterministically from chunk metadata in validator.py, never trusted
straight from model output.

If the model's output can't be parsed as valid JSON even after one retry,
raise SummarizationDegraded so main.py can fall back to a plain-text
summary rather than failing the whole request.
"""

import json
import os
from typing import List

from groq import Groq

from app.models import Chunk

MODEL = "openai/gpt-oss-120b"

# Free-tier TPM limit for this model is 8000 (prompt + completion combined).
# Budget conservatively: leave room for the system prompt (~300 tokens) and
# completion (long summaries can run ~1500-2000 tokens), so cap the chunk
# text we send to roughly 4500 tokens' worth of characters.
MAX_PROMPT_CHARS = 13000
CHARS_PER_TOKEN_ESTIMATE = 4


def select_chunks_within_budget(chunks: List[Chunk], max_chars: int = MAX_PROMPT_CHARS) -> tuple[List[Chunk], bool]:
    """
    Returns (chunks_to_send, was_truncated).

    If the full chunk set fits in the budget, sends everything. Otherwise,
    samples evenly across the whole document (not just the first N pages)
    so a long document's summary still reflects its full span, and reports
    that truncation happened so the caller can be honest with the user
    about it rather than silently dropping content.
    """
    total_chars = sum(len(c.text) for c in chunks)
    if total_chars <= max_chars:
        return chunks, False

    # Evenly sample chunk indices across the full list to preserve document
    # breadth, then keep them in original order.
    target_count = max(1, int(len(chunks) * (max_chars / total_chars)))
    stride = len(chunks) / target_count
    sampled_indices = sorted({int(i * stride) for i in range(target_count)})
    sampled = [chunks[i] for i in sampled_indices]

    # Still trim further if the sampled set is somehow over budget (uneven chunk sizes).
    running_total = 0
    final = []
    for c in sampled:
        if running_total + len(c.text) > max_chars:
            break
        final.append(c)
        running_total += len(c.text)

    return final, True

SYSTEM_PROMPT = """You are a precise document summarization assistant.
You will be given a document split into labeled chunks, each with an id and page number.

Produce a JSON object with exactly this shape:
{
  "short": [{"text": "...", "chunk_ids": ["c1"]}, ...],
  "medium": [{"text": "...", "chunk_ids": ["c1", "c2"]}, ...],
  "long": [{"text": "...", "chunk_ids": ["c1"]}, ...]
}

Rules:
- "short" should have 2-3 claims, "medium" 4-6, "long" 7-12.
- Every claim's chunk_ids MUST be ids that actually appear in the provided chunks.
- Do NOT include page numbers in your output — only chunk_ids. Page numbers are resolved separately.
- Do NOT invent information that isn't in the provided chunks.
- Respond with ONLY the JSON object. No markdown fences, no commentary.
"""


class SummarizationError(Exception):
    pass


def _build_user_prompt(chunks: List[Chunk]) -> str:
    lines = [f"[{c.id} | page {c.page_number}] {c.text}" for c in chunks]
    return "Document chunks:\n\n" + "\n\n".join(lines)


def _call_groq(client: Groq, chunks: List[Chunk], strict: bool = False) -> str:
    system = SYSTEM_PROMPT
    if strict:
        system += "\n\nIMPORTANT: Your previous response was not valid JSON. Respond with ONLY a valid JSON object, nothing else."

    completion = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": _build_user_prompt(chunks)},
        ],
        temperature=0.2,
        max_tokens=3000,
    )
    return completion.choices[0].message.content


def generate_raw_claims(chunks: List[Chunk]) -> tuple[dict, bool]:
    """
    Returns (parsed {short, medium, long} dict, was_truncated).
    Raises SummarizationError if the model output can't be parsed after a retry,
    or if the Groq call fails outright (e.g. rate limited) — callers should
    catch this and degrade gracefully rather than crash the request.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise SummarizationError("GROQ_API_KEY is not configured.")

    client = Groq(api_key=api_key)

    chunks_to_send, was_truncated = select_chunks_within_budget(chunks)

    last_error = None
    for attempt, strict in enumerate([False, True]):
        try:
            raw = _call_groq(client, chunks_to_send, strict=strict)
            cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed = json.loads(cleaned)
            if not all(k in parsed for k in ("short", "medium", "long")):
                raise ValueError("Missing required keys in model output.")
            return parsed, was_truncated
        except Exception as e:
            last_error = e
            continue

    raise SummarizationError(f"Could not get a valid structured summary from the model: {last_error}")
