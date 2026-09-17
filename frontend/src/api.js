const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API error ${res.status}: ${body}`);
  }
  return res.json();
}

export const api = {
  startChat: (language) =>
    request("/api/chat/start", { method: "POST", body: JSON.stringify({ language }) }),

  sendMessage: (sessionId, message, language) =>
    request("/api/chat/message", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, message, language }),
    }),

  getSources: () => request("/api/sources"),

  health: () => request("/api/health"),

  // Best-effort: hands over a transcript that happened on the offline
  // engine once connectivity returns. Never blocks the UI on failure.
  sendSync: (sessionId, language, turns) =>
    request("/api/sync", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, language, turns }),
    }),
};

export default api;
