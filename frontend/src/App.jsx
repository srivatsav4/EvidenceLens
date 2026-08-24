import React, { useState } from "react";
import UploadPanel from "./UploadPanel.jsx";
import SummaryView from "./SummaryView.jsx";
import SourcePanel from "./SourcePanel.jsx";
import { uploadDocument, summarizeDocument } from "./api.js";

// stage: "idle" | "processing" | "results" | "error"
export default function App() {
  const [stage, setStage] = useState("idle");
  const [summary, setSummary] = useState(null);
  const [uploadWarning, setUploadWarning] = useState(null);
  const [error, setError] = useState(null);
  const [activeClaim, setActiveClaim] = useState(null);

  async function handleFileSelected(file) {
    setStage("processing");
    setError(null);
    setActiveClaim(null);
    try {
      const uploaded = await uploadDocument(file);
      setUploadWarning(uploaded.warning);
      const result = await summarizeDocument(uploaded.document_id);
      setSummary(result);
      setStage("results");
    } catch (err) {
      setError(err.message || "Something went wrong.");
      setStage("error");
    }
  }

  function reset() {
    setStage("idle");
    setSummary(null);
    setError(null);
    setActiveClaim(null);
    setUploadWarning(null);
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>EvidenceLens</h1>
        <p className="tagline">Don't just trust the summary. See the evidence behind it.</p>
      </header>

      {stage === "idle" && (
        <UploadPanel onFileSelected={handleFileSelected} loading={false} />
      )}

      {stage === "processing" && (
        <UploadPanel onFileSelected={() => {}} loading={true} />
      )}

      {stage === "error" && (
        <div className="error-panel">
          <p>{error}</p>
          <button onClick={reset}>Try another document</button>
        </div>
      )}

      {stage === "results" && summary && (
        <div className="results">
          {uploadWarning && <p className="warning-banner">{uploadWarning}</p>}
          {summary.llm_degraded && (
            <p className="warning-banner">
              This document is long — the summary was generated from a representative
              sample of pages (evenly spread across the whole document) to fit free-tier
              AI service limits, rather than the full text.
            </p>
          )}
          <button className="reset-button" onClick={reset}>
            Upload another document
          </button>
          <div className="results-grid">
            <SummaryView
              summary={summary}
              activeClaimId={activeClaim?.id}
              onClaimClick={(claim) => claim.validated && setActiveClaim(claim)}
            />
            <SourcePanel
              chunks={summary.chunks}
              highlightedChunkIds={activeClaim?.chunk_ids}
            />
          </div>
        </div>
      )}
    </div>
  );
}
