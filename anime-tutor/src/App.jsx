import { lazy, Suspense, useState, useEffect } from "react";
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import {
  createSession, fetchProblem, submitAnswer, sendChatMessage,
  getCurrentUser, logoutUser, requestHint, fetchSessionResume,
} from "./api/client";
import AuthScreen from "./components/AuthScreen";
import CharacterSelect from "./components/CharacterSelect";
import ModeSelect from "./components/ModeSelect";
import TopicSelect from "./components/TopicSelect";
import CharacterPanel from "./components/CharacterPanel";
import SessionHeader from "./components/SessionHeader";
import ProblemCard from "./components/ProblemCard";
import ReactionPanel from "./components/ReactionPanel";
import HistoryDetailPage from "./pages/HistoryDetailPage";
import HistoryPage from "./pages/HistoryPage";
import AccountPage from "./pages/AccountPage";
import PrivacyPage from "./pages/PrivacyPage";
import TermsPage from "./pages/TermsPage";
import NotFoundPage from "./pages/NotFoundPage";
import DashboardPage from "./pages/DashboardPage";
import SyllabusPage from "./pages/SyllabusPage";
import Layout from "./pages/Layout";
import TopNav from "./components/TopNav";
import PageTransition from "./components/PageTransition";

const ChatWindow = lazy(() => import("./components/ChatWindow"));
const ACTIVE_SESSION_KEY = "animeTutorActiveSession";

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const [phase, setPhase]             = useState("checking");
  const [currentUser, setCurrentUser] = useState(null);
  const [selectedPersona, setSelectedPersona] = useState(null);
  const [selectedMode, setSelectedMode]       = useState(null);
  const [pendingTopic, setPendingTopic]       = useState(null); // from SyllabusPage startTopic
  const [sessionId, setSessionId]     = useState(null);
  const [problem, setProblem]         = useState(null);
  const [result, setResult]           = useState(null);
  const [hint, setHint]               = useState(null);
  const [chatMessages, setChatMessages]     = useState([]);
  const [chatStreak, setChatStreak]         = useState(0);
  const [chatDifficulty, setChatDifficulty] = useState(1);
  const [currentMood, setCurrentMood] = useState("default");
  const [loading, setLoading]         = useState(false);
  const [error, setError]             = useState(null);

  // ── Auth check on load ──────────────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false;

    async function initializeApp() {
      try {
        const user = await getCurrentUser();
        if (cancelled) return;
        setCurrentUser(user);

        const savedSessionId = sessionStorage.getItem(ACTIVE_SESSION_KEY);
        if (savedSessionId) {
          try {
            const session = await fetchSessionResume(savedSessionId);
            if (cancelled) return;

            setSessionId(session.session_id);
            setSelectedPersona(session.persona_id);
            setSelectedMode(session.mode);
            setChatStreak(session.streak);
            setChatDifficulty(session.difficulty);
            setCurrentMood("default");
            setResult(null);
            setHint(null);

            if (session.mode === "chat") {
              setChatMessages(session.conversation_history);
              setPhase("chat");
              return;
            }

            setChatMessages([]);
            if (session.active_problem) {
              setProblem(session.active_problem);
            } else {
              const nextProblem = await fetchProblem(session.session_id);
              if (cancelled) return;
              setProblem(nextProblem);
            }
            setPhase("problem");
            return;
          } catch (resumeError) {
            if (cancelled) return;
            setError(`Could not resume the saved session: ${resumeError.message}`);
            setPhase("select");
            return;
          }
        }

        const startTopic = location.state?.startTopic ?? null;
        if (startTopic) {
          setPendingTopic(startTopic);
          setPhase("select");
        } else if (location.pathname === "/" || location.pathname === "") {
          navigate("/dashboard", { replace: true });
        } else {
          setPhase("select");
        }
      } catch {
        if (!cancelled) setPhase("auth");
      }
    }

    initializeApp();
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function handleAuthenticated(user) {
    setCurrentUser(user);
    setError(null);
    setPhase("select");
    navigate("/dashboard");
  }

  async function handleLogout() {
    setLoading(true);
    try { await logoutUser(); } catch { /* fall through */ } finally {
      setCurrentUser(null);
      setSessionId(null);
      sessionStorage.removeItem(ACTIVE_SESSION_KEY);
      setSelectedPersona(null);
      setSelectedMode(null);
      setProblem(null);
      setResult(null);
      setChatMessages([]);
      setPendingTopic(null);
      setLoading(false);
      setPhase("auth");
      navigate("/");
    }
  }

  function handleSelectCharacter(personaId) {
    setError(null);
    setSelectedPersona(personaId);
    setPhase("mode");
  }

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
      sessionStorage.setItem(ACTIVE_SESSION_KEY, session.session_id);
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

  async function handleSelectTopic(topicId) {
    setLoading(true);
    setError(null);
    try {
      const session = await createSession(selectedPersona, selectedMode, topicId);
      setSessionId(session.session_id);
      sessionStorage.setItem(ACTIVE_SESSION_KEY, session.session_id);
      setCurrentMood("default");
      const prob = await fetchProblem(session.session_id, topicId);
      setProblem(prob);
      setHint(null);
      setPendingTopic(null); // consumed
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

  async function handleSubmit(answer) {
    setLoading(true);
    setError(null);
    setHint(null);
    try {
      const res = await submitAnswer(sessionId, problem.problem_id, answer);
      setResult(res);
      setCurrentMood(res.event_category ?? "default");
      setPhase("reaction");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function handleHint() {
    setLoading(true);
    setError(null);
    try {
      const res = await requestHint(sessionId, problem.problem_id);
      setHint(res.hint);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function handleNextProblem() {
    if (result?.event_category === "not_serious") {
      setResult(null);
      setHint(null);
      setPhase("problem");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const prob = await fetchProblem(sessionId);
      setProblem(prob);
      setResult(null);
      setHint(null);
      setPhase("problem");
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  async function handleSendChatMessage(text, file = null) {
    setChatMessages((prev) => [...prev, { role: "user", content: text || "", fileName: file?.name ?? null }]);
    setLoading(true);
    setError(null);
    try {
      const res = await sendChatMessage(sessionId, text, file);
      setChatMessages((prev) => [...prev, { role: "assistant", content: res.reply }]);
      setCurrentMood(res.mood ?? "default");
      setChatStreak(res.streak ?? 0);
      setChatDifficulty(res.difficulty ?? 1);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }

  function handleQuit() {
    setSessionId(null);
    sessionStorage.removeItem(ACTIVE_SESSION_KEY);
    setSelectedPersona(null);
    setSelectedMode(null);
    setProblem(null);
    setResult(null);
    setHint(null);
    setChatMessages([]);
    setChatStreak(0);
    setChatDifficulty(1);
    setError(null);
    setCurrentMood("default");
    setPhase("select");
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  if (phase === "checking") {
    return (
      <div className="min-h-screen bg-indigo-950 text-slate-100 flex items-center justify-center">
        <span className="text-slate-500 text-sm animate-pulse">Loading...</span>
      </div>
    );
  }

  if (phase === "auth") {
    return (
      <div className="min-h-screen bg-indigo-950 text-slate-100 flex items-center justify-center p-8">
        <AuthScreen onAuthenticated={handleAuthenticated} loading={loading} setLoading={setLoading} />
      </div>
    );
  }

  if (phase === "select") {
    return (
      <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col">
        <TopNav currentUser={currentUser} onLogout={handleLogout} />
        <PageTransition key="select" className="flex-1 flex items-center justify-center p-8 relative">
          {error && <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">{error}</div>}
          <CharacterSelect onSelect={handleSelectCharacter} loading={loading} />
        </PageTransition>
      </div>
    );
  }

  if (phase === "mode") {
    return (
      <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col">
        <TopNav currentUser={currentUser} onLogout={handleLogout} />
        <PageTransition key="mode" className="flex-1 flex items-center justify-center p-8 relative">
          {error && <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">{error}</div>}
          <ModeSelect onSelect={handleSelectMode} onBack={handleBackToCharacterSelect} loading={loading} />
        </PageTransition>
      </div>
    );
  }

  if (phase === "topic") {
    return (
      <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col">
        <TopNav currentUser={currentUser} onLogout={handleLogout} />
        <PageTransition key="topic" className="flex-1 flex items-center justify-center p-8 relative">
          {error && <div className="absolute top-4 px-4 py-2 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm">{error}</div>}
          <TopicSelect
            onSelect={handleSelectTopic}
            onBack={handleBackToModeSelect}
            loading={loading}
            preSelectedTopic={pendingTopic}
          />
        </PageTransition>
      </div>
    );
  }

  // Active session — no TopNav, split layout
  const isChat = phase === "chat";
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-indigo-950 text-slate-100">
      <CharacterPanel personaId={selectedPersona} mood={currentMood} />
      <div className={`flex flex-col flex-1 ${isChat ? "overflow-hidden" : "overflow-y-auto"}`}>
        {error && (
          <div className="mx-6 mt-4 px-4 py-2 bg-red-900/50 border border-red-700 rounded text-red-300 text-sm shrink-0">
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
            {phase === "problem"  && <ProblemCard problem={problem} onSubmit={handleSubmit} onHint={handleHint} loading={loading} hint={hint} />}
            {phase === "reaction" && <ReactionPanel result={result} onNext={handleNextProblem} loading={loading} />}
            {phase === "chat" && (
              <Suspense fallback={<p className="text-center text-slate-500 text-sm">Loading chat...</p>}>
                <ChatWindow messages={chatMessages} onSend={handleSendChatMessage} loading={loading} />
              </Suspense>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function AppRouter() {
  return (
    <Routes>
      <Route path="/"                    element={<App />} />
      <Route path="/history"             element={<Layout><HistoryPage /></Layout>} />
      <Route path="/history/:sessionId"  element={<Layout><HistoryDetailPage /></Layout>} />
      <Route path="/account"             element={<Layout><AccountPage /></Layout>} />
      <Route path="/dashboard"           element={<Layout><DashboardPage /></Layout>} />
      <Route path="/syllabus"            element={<Layout><SyllabusPage /></Layout>} />
      <Route path="/privacy"             element={<PrivacyPage />} />
      <Route path="/terms"               element={<TermsPage />} />
      <Route path="*"                    element={<NotFoundPage />} />
    </Routes>
  );
}
