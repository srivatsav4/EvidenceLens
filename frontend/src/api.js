const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function uploadDocument(file) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/api/upload`, { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Upload failed.");
  return data;
}

export async function summarizeDocument(documentId) {
  const res = await fetch(`${API_BASE}/api/summarize/${documentId}`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Summarization failed.");
  return data;
}