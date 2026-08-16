const BASE_URL = "http://localhost:8000";

async function request(path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// POST /session — creates a new session for the given persona.
// mode: "qna" (default, existing flow) | "chat" (v2.2 free-form chat mode)
// topic: only meaningful for chat mode — qna mode still sets its topic later via /problem
export function createSession(personaId, mode = "qna", topic = null) {
  return request("/session", { persona_id: personaId, mode, topic });
}

// POST /problem — fetches the next problem for this session.
// topic is optional: pass it when the user just picked a topic; omit (or
// pass null) on "next problem" within the same topic — the backend remembers
// the session's current topic either way.
export function fetchProblem(sessionId, topic = null) {
  return request("/problem", { session_id: sessionId, topic });
}

// POST /submit — submits an answer (or give_up=true for a hint)
export function submitAnswer(sessionId, problemId, answer, giveUp = false) {
  return request("/submit", {
    session_id: sessionId,
    problem_id: problemId,
    answer: giveUp ? null : answer,
    give_up: giveUp,
  });
}

// POST /chat — v2.2 free-form chat mode. Returns { reply, mood, streak, difficulty }.
export function sendChatMessage(sessionId, message) {
  return request("/chat", { session_id: sessionId, message });
}
