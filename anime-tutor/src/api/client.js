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

// POST /session — creates a new session for the given persona
export function createSession(personaId) {
  return request("/session", { persona_id: personaId });
}

// POST /problem — fetches the next problem for this session
export function fetchProblem(sessionId) {
  return request("/problem", { session_id: sessionId });
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
