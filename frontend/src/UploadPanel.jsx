import React, { useCallback, useState } from "react";

const ACCEPTED_TYPES = ["application/pdf", "image/png", "image/jpeg"];

export default function UploadPanel({ onFileSelected, loading }) {
  const [isDragging, setIsDragging] = useState(false);
  const [localError, setLocalError] = useState(null);

  const handleFiles = useCallback(
    (files) => {
      setLocalError(null);
      const file = files[0];
      if (!file) return;
      if (!ACCEPTED_TYPES.includes(file.type)) {
        setLocalError("Please upload a PDF, PNG, or JPG file.");
        return;
      }
      onFileSelected(file);
    },
    [onFileSelected]
  );

  return (
    <div
      className={`upload-panel ${isDragging ? "dragging" : ""}`}
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
    >
      <p className="upload-title">Drag & drop a PDF or image here</p>
      <p className="upload-subtitle">or</p>
      <label className="upload-button">
        Choose a file
        <input
          type="file"
          accept=".pdf,.png,.jpg,.jpeg"
          style={{ display: "none" }}
          disabled={loading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </label>
      {loading && <p className="upload-status">Processing document…</p>}
      {localError && <p className="upload-error">{localError}</p>}
    </div>
  );
}
