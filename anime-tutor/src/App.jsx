import { useState } from "react";
import { createSession, fetchProblem, submitAnswer, sendChatMessage } from "./api/client";
import CharacterSelect from "./components/CharacterSelect";
import ModeSelect from "./components/ModeSelect";
import TopicSelect from "./components/TopicSelect";
import CharacterPanel from "./components/CharacterPanel";
import SessionHeader from "./components/SessionHeader";
import ProblemCard from "./components/ProblemCard";
import ReactionPanel from "./components/ReactionPanel";
import ChatWindow from "./components/ChatWindow";

export default function App() {
  const [phase, setPhase]         = useState("select"); // "select" | "mode" | "topic" | "problem" | "reaction" | "chat"
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedMode, setSelectedMode]       = useState(null); // "qna" | "chat" — chosen before the session exists
  const [sessionId, setSessionId] = useState(null);

  // qna-mode state — unchanged from before
  const [problem, setProblem]     = useState(null);
  const [result, setResult]       = useState(null);

  // chat-mode state — new. Kept separate from problem/result rather than
  // unifying, so the existing qna handlers below stay untouched.
  const [chatMessages, setChatMessages]     = useState([]);
  const [chatStreak, setChatStreak]         = useState(0);
  const [chatDifficulty, setChatDifficulty] = useState(1);

  const [currentMood, setCurrentMood] = useState("default"); // persists across phases, shared by both modes
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  // ── Character select — no API call anymore, just stores the choice ────────
  function handleSelectCharacter(personaId) {
    setError(null);
    setSelectedPersona(personaId);
    setPhase("mode");
  }

  // ── Mode select — no API call, just stores the choice ──────────────────────
  function handleSelectMode(mode) {
    setError(null);
    setSelectedMode(mode);
    setPhase("topic");
  }

  // ── Topic select — THIS is where the session actually gets created now,
  // since chat mode needs persona + mode + topic all known at once ──────────
  async function handleSelectTopic(topicId) {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession(selectedPersona, selectedMode, topicId);
      setSessionId(session.session_id);
      setCurrentMood("default");

      if (selectedMode === "chat") {
        setChatMessages([]);
        setChatStreak(0);
        setChatDifficulty(session.difficulty);
        setPhase("chat");
      } else {
        const prob = await fetchProblem(session.session_id, topicId);
        setProblem(prob);
        setPhase("problem");
      }
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
  async function handleSendChatMessage(text) {
    setChatMessages((prev) => [...prev, { role: "user", content: text }]);
    setLoading(true);
    setError(null);
    try {
      const res = await sendChatMessage(sessionId, text);
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
        <CharacterSelect onSelect={handleSelectCharacter} loading={loading} />
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
