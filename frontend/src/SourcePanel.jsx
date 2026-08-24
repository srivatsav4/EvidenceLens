import React, { useEffect, useRef } from "react";

export default function SourcePanel({ chunks, highlightedChunkIds }) {
  const refs = useRef({});

  useEffect(() => {
    if (highlightedChunkIds && highlightedChunkIds.length > 0) {
      const el = refs.current[highlightedChunkIds[0]];
      if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
  }, [highlightedChunkIds]);

  const grouped = {};
  for (const chunk of chunks) {
    (grouped[chunk.page_number] ||= []).push(chunk);
  }

  return (
    <div className="source-panel">
      <p className="source-panel-title">Source document</p>
      {Object.entries(grouped).map(([pageNumber, pageChunks]) => (
        <div key={pageNumber} className="source-page">
          <p className="source-page-label">Page {pageNumber}</p>
          {pageChunks.map((chunk) => (
            <p
              key={chunk.id}
              ref={(el) => (refs.current[chunk.id] = el)}
              className={`source-chunk ${
                highlightedChunkIds?.includes(chunk.id) ? "highlighted" : ""
              }`}
            >
              {chunk.text}
            </p>
          ))}
        </div>
      ))}
    </div>
  );
}
