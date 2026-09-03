import { useState, useEffect } from "react";
import { createSession, fetchProblem, submitAnswer, sendChatMessage, getCurrentUser, logoutUser, fetchSessionHistory } from "./api/client";
import AuthScreen from "./components/AuthScreen";
import CharacterSelect from "./components/CharacterSelect";
import ModeSelect from "./components/ModeSelect";
import TopicSelect from "./components/TopicSelect";
import CharacterPanel from "./components/CharacterPanel";
import SessionHeader from "./components/SessionHeader";
import ProblemCard from "./components/ProblemCard";
import ReactionPanel from "./components/ReactionPanel";
import ChatWindow from "./components/ChatWindow";
import SessionHistory from "./components/SessionHistory";

export default function App() {
  // "checking" — brief initial state while we ask /auth/me if a session
  // cookie already exists (page refresh, or just landed back from Google's
  // OAuth redirect). "auth" — logged out, show the login/register screen.
  // Everything else is unchanged from before, just gated behind these two.
  const [phase, setPhase]         = useState("checking");
  const [currentUser, setCurrentUser] = useState(null);
  const [sessionHistory, setSessionHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);

  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedMode, setSelectedMode]       = useState(null); // "qna" | "chat" — chosen before the session exists
  const [sessionId, setSessionId] = useState(null);

  // qna-mode state — unchanged from before
  const [problem, setProblem]     = useState(null);
  const [result, setResult]       = useState(null);

  // chat-mode state — unchanged from before
  const [chatMessages, setChatMessages]     = useState([]);
  const [chatStreak, setChatStreak]         = useState(0);
  const [chatDifficulty, setChatDifficulty] = useState(1);

  const [currentMood, setCurrentMood] = useState("default"); // persists across phases, shared by both modes
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  // ── Auth check on load ──────────────────────────────────────────────────────
  useEffect(() => {
    getCurrentUser()
      .then((user) => {
        setCurrentUser(user);
        setPhase("select");
      })
      .catch(() => {
        // No valid cookie — not an error state, just means "show login"
        setPhase("auth");
      });
  }, []);

  function handleAuthenticated(user) {
    setCurrentUser(user);
    setError(null);
    setPhase("select");
  }

  async function handleLogout() {
    setLoading(true);
    try {
      await logoutUser();
    } catch {
      // Even if the logout call fails (e.g. network hiccup), still clear
      // local state and drop back to the login screen — staying "logged
      // in" client-side with a possibly-stale cookie is worse than forcing
      // a fresh login.
    } finally {
      setCurrentUser(null);
      setSessionId(null);
      setSelectedPersona(null);
      setSelectedMode(null);
      setProblem(null);
      setResult(null);
      setChatMessages([]);
      setLoading(false);
      setPhase("auth");
    }
  }

  // ── Character select — no API call anymore, just stores the choice ────────
  function handleSelectCharacter(personaId) {
    setError(null);
    setSelectedPersona(personaId);
    setPhase("mode");
  }

  async function handleViewHistory() {
    setHistoryLoading(true);
    setHistoryError(null);
    setPhase("history");
    try {
      setSessionHistory(await fetchSessionHistory());
    } catch (e) {
      setHistoryError(e.message);
    } finally {
      setHistoryLoading(false);
    }
  }

  // ── Mode select — chat starts immediately; Q&A still needs a topic ────────
  async function handleSelectMode(mode) {
    setError(null);
    setSelectedMode(mode);
    if (mode !== "chat") {
      setPhase("topic");
      return;
    }

    setLoading(true);
    try {
      const session = await createSession(selectedPersona, mode);
      setSessionId(session.session_id);
      setCurrentMood("default");
      setChatMessages([]);
      setChatStreak(0);
      setChatDifficulty(session.difficulty);
      setPhase("chat");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── Topic select — Quick Practice creates its session here ─────────────────
  async function handleSelectTopic(topicId) {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession(selectedPersona, selectedMode, topicId);
      setSessionId(session.session_id);
      setCurrentMood("default");

      const prob = await fetchProblem(session.session_id, topicId);
      setProblem(prob);
      setPhase("problem");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleBackToCharacterSelect() {
    setError(null);
    setSelectedPersona(null);
    setSelectedMode(null);
    setPhase("select");
  }

  function handleBackToModeSelect() {
    setError(null);
    setSelectedMode(null);
    setPhase("mode");
  }

  // ── qna mode handlers — unchanged from before ───────────────────────────────
  async function handleSubmit(answer) {
    setLoading(true);
    setError(null);
    try {
      const res = await submitAnswer(sessionId, problem.problem_id, answer);
      setResult(res);
      setCurrentMood(res.event_category ?? "default");
      setPhase("reaction");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleHint() {
    setLoading(true);
    setError(null);
    try {
      const res = await submitAnswer(sessionId, problem.problem_id, null, true);
      setResult(res);
      setCurrentMood(res.event_category ?? "default");
      setPhase("reaction");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleNextProblem() {
    setLoading(true);
    setError(null);
    try {
      const prob = await fetchProblem(sessionId);
      setProblem(prob);
      setResult(null);
      // mood stays as the last reaction until the next answer — intentional
      setPhase("problem");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  // ── chat mode handler — new ─────────────────────────────────────────────────
  async function handleSendChatMessage(text, file = null) {
    const displayContent = text || "";
    const fileName = file?.name ?? null;
    setChatMessages((prev) => [...prev, { role: "user", content: displayContent, fileName }]);
    setLoading(true);
    setError(null);
    try {
      const res = await sendChatMessage(sessionId, text, file);
      setChatMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setCurrentMood(res.mood ?? "default");
      setChatStreak(res.streak ?? 0);
      setChatDifficulty(res.difficulty ?? 1);
    } catch (e) {
      setError(e.message);
      // the optimistically-added user message stays in the list even on
      // error — simplest behavior for now, revisit if it feels wrong in practice
    } finally {
      setLoading(false);
    }
  }

  function handleQuit() {
    setSessionId(null);
    setSelectedPersona(null);
    setSelectedMode(null);
    setProblem(null);
    setResult(null);
    setChatMessages([]);
    setChatStreak(0);
    setChatDifficulty(1);
    setError(null);
    setCurrentMood("default");
    setPhase("select");
  }

  // Checking auth — brief loading state, no flash of the login screen on
  // every refresh for someone who's already logged in
  if (phase === "checking") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        <span className="text-slate-500 text-sm animate-pulse">Loading...</span>
      </div>
    );
  }

  // Auth gate — logged out, show login/register
  if (phase === "auth") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        <AuthScreen onAuthenticated={handleAuthenticated} loading={loading} setLoading={setLoading} />
      </div>
    );
  }

  // Character select — full screen centered
  if (phase === "select") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        {error && (
          <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700
                          rounded text-red-300 text-sm">
            {error}
          </div>
        )}
        <button
          onClick={handleLogout}
          className="absolute top-4 right-4 text-slate-500 text-xs hover:text-slate-300
                     transition-colors"
        >
          {currentUser?.email} · Log out
        </button>
        <div className="flex flex-col items-center gap-5 w-full">
          <CharacterSelect onSelect={handleSelectCharacter} loading={loading} />
          <button
            type="button"
            onClick={handleViewHistory}
            className="text-slate-400 text-sm hover:text-slate-100 underline underline-offset-4 transition-colors"
          >
            View session history
          </button>
        </div>
      </div>
    );
  }

  if (phase === "history") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        <SessionHistory
          sessions={sessionHistory}
          loading={historyLoading}
          error={historyError}
          onBack={() => { setHistoryError(null); setPhase("select"); }}
        />
      </div>
    );
  }

  // Mode select — full screen centered, same shell
  if (phase === "mode") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        {error && (
          <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700
                          rounded text-red-300 text-sm">
            {error}
          </div>
        )}
        <ModeSelect
          onSelect={handleSelectMode}
          onBack={handleBackToCharacterSelect}
          loading={loading}
        />
      </div>
    );
  }

  // Topic select — full screen centered, same shell
  if (phase === "topic") {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-8">
        {error && (
          <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700
                          rounded text-red-300 text-sm">
            {error}
          </div>
        )}
        <TopicSelect
          onSelect={handleSelectTopic}
          onBack={handleBackToModeSelect}
          loading={loading}
        />
      </div>
    );
  }

  // Session — split layout. Chat needs the right column to NOT scroll as a
  // whole (only ChatWindow's internal message list should scroll), and needs
  // its content area to fill height rather than center a small fixed card —
  // both differ from qna mode's problem/reaction layout, so branch on it.
  const isChat = phase === "chat";

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">

      {/* Left half — character image, mood-driven, shared by both modes */}
      <CharacterPanel personaId={selectedPersona} mood={currentMood} />

      {/* Right half — header + problem/reaction OR chat */}
      <div className={`flex flex-col flex-1 ${isChat ? "overflow-hidden" : "overflow-y-auto"}`}>

        {error && (
          <div className="mx-6 mt-4 px-4 py-2 bg-red-900/50 border border-red-700
                          rounded text-red-300 text-sm shrink-0">
            {error}
          </div>
        )}

        <div className={`flex flex-col flex-1 gap-4 px-6 py-6 ${isChat ? "min-h-0" : ""}`}>
          <SessionHeader
            personaId={selectedPersona}
            streak={isChat ? chatStreak : (result?.streak ?? 0)}
            difficulty={isChat ? chatDifficulty : (problem?.difficulty ?? 1)}
            onQuit={handleQuit}
            userEmail={currentUser?.email}
            onLogout={handleLogout}
          />

          <div className={isChat ? "flex-1 min-h-0 flex flex-col" : "flex-1 flex flex-col justify-center"}>
            {phase === "problem" && (
              <ProblemCard
                problem={problem}
                onSubmit={handleSubmit}
                onHint={handleHint}
                loading={loading}
              />
            )}

            {phase === "reaction" && (
              <ReactionPanel
                result={result}
                onNext={handleNextProblem}
                loading={loading}
              />
            )}

            {phase === "chat" && (
              <ChatWindow
                messages={chatMessages}
                onSend={handleSendChatMessage}
                loading={loading}
              />
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
