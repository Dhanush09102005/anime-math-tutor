const BASE_URL = "http://localhost:8000";

async function request(path, body, method = "POST") {
  const options = {
    method,
    // Required for the httpOnly auth cookie to be sent on every request and
    // stored after login/register — without this, the browser silently
    // drops the cookie and every protected route 401s even right after a
    // successful login.
    credentials: "include",
  };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  const res = await fetch(`${BASE_URL}${path}`, options);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export function registerUser(email, password) {
  return request("/auth/register", { email, password });
}

export function loginUser(email, password) {
  return request("/auth/login", { email, password });
}

export function logoutUser() {
  return request("/auth/logout", undefined, "POST");
}

export function fetchSessionHistory() {
  return request("/sessions", undefined, "GET");
}

// GET /auth/me — used on app load to check "is there already a valid auth
// cookie" (handles page refresh, and the redirect back from Google OAuth).
// Throws (via request()'s !res.ok check) if not authenticated — caller
// should catch and treat that as "show the login screen".
export function getCurrentUser() {
  return request("/auth/me", undefined, "GET");
}

// Not a fetch call — this kicks off the OAuth redirect flow, so it's just a
// URL the caller navigates the browser to directly (window.location.href = ...).
export function googleLoginUrl() {
  return `${BASE_URL}/auth/oauth/google/login`;
}

// ── Session / problem / submit (unchanged logic, now cookie-authenticated) ───

// POST /session — creates a new session for the given persona.
// mode: "qna" (default, existing flow) | "chat" (v2.2 free-form chat mode)
// topic: only meaningful for chat mode — qna mode still sets it later via /problem
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

// POST /chat — v2.0.0 teaching mode. Accepts text + optional file (image/PDF).
export async function sendChatMessage(sessionId, message, file = null) {
  const form = new FormData();
  form.append("session_id", sessionId);
  form.append("message", message || "");
  if (file) form.append("file", file);

  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    credentials: "include", // same cookie requirement as request() above
    body: form,
    // No Content-Type header — browser sets multipart boundary automatically
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}
