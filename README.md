# EvidenceLens

**Don't just trust the summary. See the evidence behind it.**

EvidenceLens is a document summary assistant. Upload a PDF or scanned image, and it
generates short/medium/long summaries — but unlike a plain "LLM summarizes your PDF"
tool, every claim in the summary can be clicked to jump to the exact page and passage
of the original document it was drawn from.

## Why this exists

Generic AI summarizers ask you to trust the model's output on faith. EvidenceLens
instead treats provenance as the actual product: every extracted page keeps its page
number from the moment text is pulled out of the document, every claim the model
generates is required to cite the chunk(s) it drew from, and every citation is
validated against the real extracted text before being shown as trustworthy — the
model is never allowed to simply assert a page number itself.

## How it works

```
PDF / image
   -> PyMuPDF (PDF) or Tesseract OCR (image), page-tagged text extraction
   -> paragraph-level chunking (each chunk keeps its page number)
   -> one structured LLM call (Groq / Llama 3.3 70B): generates short/medium/long
      claims, each tagged with the chunk_id(s) it used
   -> evidence validation: checks that cited chunk_ids exist and that claim text
      lexically overlaps the cited chunk -- unverifiable claims are flagged, not
      hidden
   -> frontend: click a claim -> highlighted source passage scrolls into view
```

## Tech stack

- **Frontend:** React (Vite)
- **Backend:** FastAPI (Python)
- **PDF extraction:** PyMuPDF
- **OCR:** Tesseract (via pytesseract)
- **LLM:** Groq API (free tier, Llama 3.3 70B)
- **Hosting:** Hugging Face Spaces (Docker), single container serving both the API and the built frontend

No paid services are required anywhere in the pipeline.

## Running locally

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your free Groq API key
uvicorn app.main:app --reload --port 8000
```
Tesseract must also be installed on your system separately (e.g. `apt install
tesseract-ocr` on Linux, `brew install tesseract` on macOS) since `pytesseract` calls
the system binary.

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```
Vite proxies `/api` requests to `http://localhost:8000` (see `vite.config.js`).

## Deploying

Push this repository to a Hugging Face Space configured with the Docker SDK. Set
`GROQ_API_KEY` as a Space **secret** (never commit it). The Dockerfile builds the
frontend and serves everything from one container on port 7860.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `GROQ_API_KEY` | Yes | Free API key from console.groq.com, used for summary/claim generation |

## Known limitations

Stated plainly rather than hidden, per honest engineering practice:

- **Evidence validation is heuristic, not proof.** Claim-to-chunk matching uses
  lexical token overlap, not a trained entailment model. It reliably catches
  hallucinated/nonexistent citations, but a claim can in principle pass the overlap
  check while still subtly misrepresenting the source. The UI's "verified" badge
  means "cited a real chunk with plausible textual overlap," not "independently
  fact-checked."
- **Page-level granularity, not sentence-level.** Clicking a claim highlights the
  paragraph-sized chunk(s) it came from, not an exact sentence or character range.
  This was an intentional scope decision to keep the system reliable within an 8-hour
  build.
- **No persistence.** Documents are processed in memory per session; there's no
  database, no history, no accounts. A server restart clears in-flight documents.
- **Free-tier rate limits apply.** The Groq free tier has request-per-minute limits;
  under heavy concurrent use the app will show a "please try again shortly" message
  rather than fail silently.

## Testing

See `TESTING.md` (added in a later phase) for the manual test matrix covering normal
PDFs, scanned PDFs, corrupted files, empty documents, and OCR edge cases.
