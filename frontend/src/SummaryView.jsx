import React, { useState } from "react";

const TABS = [
  { key: "summary_short", label: "Short" },
  { key: "summary_medium", label: "Medium" },
  { key: "summary_long", label: "Long" },
];

export default function SummaryView({ summary, activeClaimId, onClaimClick }) {
  const [tab, setTab] = useState("summary_short");
  const claims = summary[tab] || [];

  return (
    <div className="summary-view">
      <div className="tabs">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${tab === t.key ? "active" : ""}`}
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </div>
      <ul className="claim-list">
        {claims.map((claim) => (
          <li
            key={claim.id}
            className={`claim ${claim.validated ? "validated" : "unverified"} ${
              activeClaimId === claim.id ? "active" : ""
            }`}
            onClick={() => onClaimClick(claim)}
            title={
              claim.validated
                ? `Click to view source (page ${claim.page_numbers.join(", ")})`
                : "This claim's source could not be confidently verified"
            }
          >
            <span className="claim-text">{claim.text}</span>
            {claim.validated ? (
              <span className="claim-badge validated-badge">
                p. {claim.page_numbers.join(", ")}
              </span>
            ) : (
              <span className="claim-badge unverified-badge">unverified</span>
            )}
          </li>
        ))}
        {claims.length === 0 && <li className="claim-empty">No claims generated.</li>}
      </ul>
    </div>
  );
}
