export const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

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

export function fetchSessionResume(sessionId) {
  return request(`/sessions/${sessionId}/resume`, undefined, "GET");
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

// PATCH /auth/profile — display name only (multipart form, matches the
// avatar upload's form-data style so both profile endpoints are consistent).
export async function updateProfile({ displayName }) {
  const form = new FormData();
  if (displayName !== undefined) form.append("display_name", displayName);

  const res = await fetch(`${BASE_URL}/auth/profile`, {
    method: "PATCH",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// POST /auth/profile/avatar — multipart file upload
export async function uploadAvatar(file) {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${BASE_URL}/auth/profile/avatar`, {
    method: "POST",
    credentials: "include",
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
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

// POST /submit — submits an answer
export function submitAnswer(sessionId, problemId, answer, giveUp = false) {
  return request("/submit", {
    session_id: sessionId,
    problem_id: problemId,
    answer: giveUp ? null : answer,
    give_up: giveUp,
  });
}

// POST /hint — asks for a non-revealing hint without submitting the answer
export function requestHint(sessionId, problemId) {
  return request("/hint", { session_id: sessionId, problem_id: problemId });
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

// GET /sessions/:id/attempts — individual attempt detail for a session
export async function fetchSessionAttempts(sessionId) {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/attempts`, {
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// POST /auth/change-password
export function changePassword(currentPassword, newPassword) {
  return request("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

// DELETE /auth/account
export async function deleteAccount() {
  const res = await fetch(`${BASE_URL}/auth/account`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
}

// GET /analytics — per-topic accuracy, attempt counts, best difficulty
export async function fetchAnalytics() {
  const res = await fetch(`${BASE_URL}/analytics`, { credentials: "include" });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

// GET /syllabus/progress — mastery status per topic
export async function fetchSyllabusProgress() {
  const res = await fetch(`${BASE_URL}/syllabus/progress`, { credentials: "include" });
  if (!res.ok) throw new Error(`Request failed: ${res.status}`);
  return res.json();
}

export function fetchQuestionPapers() {
  return request("/question-banks", undefined, "GET");
}

export function fetchQuestionPaper(paperId) {
  return request(`/question-banks/${paperId}`, undefined, "GET");
}

export function createPaperAttempt(paperId) {
  return request(`/question-banks/${paperId}/attempts`, undefined, "POST");
}

export function fetchPaperAttempt(attemptId) {
  return request(`/question-banks/attempts/${attemptId}`, undefined, "GET");
}

export function savePaperAnswers(attemptId, answers) {
  return request(`/question-banks/attempts/${attemptId}/answers`, { answers }, "PUT");
}

export function submitPaperAttempt(attemptId, answers) {
  return request(`/question-banks/attempts/${attemptId}/submit`, { answers });
}

export function createQuestionPaper(paper) {
  return request("/question-banks", paper);
}

export function fetchStudentPaperProgress() {
  return request("/question-banks/admin/progress", undefined, "GET");
}
