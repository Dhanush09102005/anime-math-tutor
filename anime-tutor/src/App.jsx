import { useState } from "react";
import { createSession, fetchProblem, submitAnswer } from "./api/client";
import CharacterSelect from "./components/CharacterSelect";
import TopicSelect from "./components/TopicSelect";
import CharacterPanel from "./components/CharacterPanel";
import SessionHeader from "./components/SessionHeader";
import ProblemCard from "./components/ProblemCard";
import ReactionPanel from "./components/ReactionPanel";

export default function App() {
  const [phase, setPhase]         = useState("select"); // "select" | "topic" | "problem" | "reaction"
  const [sessionId, setSessionId] = useState(null);
  const [problem, setProblem]     = useState(null);
  const [result, setResult]       = useState(null);
  const [currentMood, setCurrentMood] = useState("default"); // persists across phases
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  async function handleSelectCharacter(personaId) {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession(personaId);
      setSessionId(session.session_id);
      setPhase("topic");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectTopic(topicId) {
    setLoading(true);
    setError(null);
    try {
      const prob = await fetchProblem(sessionId, topicId);
      setProblem(prob);
      setCurrentMood("default");
      setPhase("problem");
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  function handleBackToCharacterSelect() {
    setSessionId(null);
    setError(null);
    setPhase("select");
  }

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

  function handleQuit() {
    setSessionId(null);
    setProblem(null);
    setResult(null);
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

  // Topic select — full screen centered, same shell as character select
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
          onBack={handleBackToCharacterSelect}
          loading={loading}
        />
      </div>
    );
  }

  // Session — split layout
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-slate-950 text-slate-100">

      {/* Left half — character image, mood-driven */}
      <CharacterPanel mood={currentMood} />

      {/* Right half — header + problem or reaction */}
      <div className="flex flex-col flex-1 overflow-y-auto">

        {error && (
          <div className="mx-6 mt-4 px-4 py-2 bg-red-900/50 border border-red-700
                          rounded text-red-300 text-sm shrink-0">
            {error}
          </div>
        )}

        <div className="flex flex-col flex-1 gap-4 px-6 py-6">
          <SessionHeader
            streak={result?.streak ?? 0}
            difficulty={problem?.difficulty ?? 1}
            onQuit={handleQuit}
          />

          <div className="flex-1 flex flex-col justify-center">
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
          </div>
        </div>

      </div>
    </div>
  );
}
