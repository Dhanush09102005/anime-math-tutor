import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchSyllabusProgress } from "../api/client";

// Ordered curriculum — prerequisites must appear before the topic that needs them.
// Each topic has an id (matches backend TOPIC_GENERATORS keys), display name,
// category, and optional prerequisites (topic ids that should be started first).
const CURRICULUM = [
  // ── Foundations ─────────────────────────────────────────────────────────────
  { id: "numbers",             name: "Playing with Numbers",     category: "Foundations",          prerequisites: [] },
  { id: "linear_equations",    name: "Linear Equations",         category: "Foundations",          prerequisites: ["numbers"] },
  { id: "logarithms",          name: "Logarithms",               category: "Foundations",          prerequisites: ["linear_equations"] },
  { id: "sets_relations",      name: "Sets & Relations",         category: "Foundations",          prerequisites: ["numbers"] },

  // ── Algebra ──────────────────────────────────────────────────────────────────
  { id: "quadratic_equations", name: "Quadratic Equations",      category: "Algebra",              prerequisites: ["linear_equations"] },
  { id: "progressions",        name: "Progressions",             category: "Algebra",              prerequisites: ["linear_equations"] },
  { id: "binomial_theorem",    name: "Binomial Theorem",         category: "Algebra",              prerequisites: ["progressions"] },
  { id: "complex_numbers",     name: "Complex Numbers",          category: "Algebra",              prerequisites: ["quadratic_equations"] },

  // ── Trigonometry ──────────────────────────────────────────────────────────────
  { id: "trigonometry",        name: "Trigonometry",             category: "Trigonometry",         prerequisites: ["linear_equations"] },

  // ── Linear Algebra ────────────────────────────────────────────────────────────
  { id: "matrices_determinants", name: "Matrices & Determinants", category: "Linear Algebra",     prerequisites: ["linear_equations"] },
  { id: "linear_algebra",      name: "Linear Algebra (Eigenvalues)", category: "Linear Algebra",  prerequisites: ["matrices_determinants"] },

  // ── Geometry ─────────────────────────────────────────────────────────────────
  { id: "coordinate_geometry", name: "Coordinate Geometry",      category: "Geometry",             prerequisites: ["linear_equations", "trigonometry"] },
  { id: "vectors_3d",          name: "Vectors & 3D Geometry",    category: "Geometry",             prerequisites: ["coordinate_geometry"] },

  // ── Calculus ─────────────────────────────────────────────────────────────────
  { id: "calculus",            name: "Derivatives & Integrals",  category: "Calculus",             prerequisites: ["trigonometry", "logarithms"] },

  // ── Probability & Statistics ──────────────────────────────────────────────────
  { id: "probability",         name: "P&C and Probability",      category: "Probability & Stats",  prerequisites: ["progressions"] },
  { id: "statistics",          name: "Statistics",               category: "Probability & Stats",  prerequisites: ["probability"] },
];

const CATEGORIES = [...new Set(CURRICULUM.map(t => t.category))];

function TopicCard({ topic, status, locked, onFindPapers }) {
  const { started, mastered, accuracy, best_difficulty } = status ?? {};

  const borderColor = mastered  ? "border-green-700"  :
                      started   ? "border-blue-800"   :
                      locked    ? "border-indigo-900"  :
                                  "border-indigo-700";

  const badgeBg     = mastered  ? "bg-green-900/50 text-green-300"  :
                      started   ? "bg-blue-900/50 text-blue-300"    :
                      locked    ? "bg-indigo-900 text-indigo-600"     :
                                  "bg-indigo-900 text-slate-400";

  const badgeText   = mastered  ? "Mastered" :
                      started   ? "In progress" :
                      locked    ? "Locked" :
                                  "Not started";

  const rankLabel   = !best_difficulty ? null :
                      best_difficulty >= 9 ? "S" :
                      best_difficulty >= 7 ? "A" :
                      best_difficulty >= 5 ? "B" :
                      best_difficulty >= 3 ? "C" : "D";

  const rankColor   = rankLabel === "S" ? "text-yellow-400" :
                      rankLabel === "A" ? "text-purple-400" :
                      rankLabel === "B" ? "text-blue-400"   :
                      rankLabel === "C" ? "text-green-400"  : "text-slate-400";

  return (
    <div className={`flex items-center justify-between px-4 py-3 rounded-lg bg-indigo-900
                     border ${borderColor} ${locked ? "opacity-50" : ""}`}>
      <div className="flex items-center gap-3 min-w-0">
        {/* Rank badge */}
        {rankLabel ? (
          <span className={`text-xs font-bold w-5 text-center ${rankColor}`}>{rankLabel}</span>
        ) : (
          <span className="w-5" />
        )}
        <div className="min-w-0">
          <p className="text-slate-100 text-sm font-medium truncate">{topic.name}</p>
          {started && !mastered && (
            <p className="text-slate-500 text-xs">{accuracy}% accuracy</p>
          )}
        </div>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        <span className={`text-xs px-2 py-0.5 rounded font-medium ${badgeBg}`}>
          {badgeText}
        </span>
        {!locked && (
          <button
            onClick={() => onFindPapers(topic.id)}
            className="pill-btn bg-indigo-700 hover:bg-indigo-600 text-slate-200"
          >
            Find papers →
          </button>
        )}
      </div>
    </div>
  );
}

export default function SyllabusPage() {
  const navigate = useNavigate();
  const [progress, setProgress] = useState({});
  const [loading, setLoading]   = useState(true);
  const [error, setError]       = useState(null);

  useEffect(() => {
    fetchSyllabusProgress()
      .then(setProgress)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  function isLocked(topic) {
    if (topic.prerequisites.length === 0) return false;
    // Locked if ANY prerequisite hasn't been started yet
    return topic.prerequisites.some(prereqId => !progress[prereqId]?.started);
  }

  function handleFindPapers(topicId) {
    navigate("/question-banks", { state: { topic: topicId } });
  }

  const totalTopics   = CURRICULUM.length;
  const masteredCount = CURRICULUM.filter(t => progress[t.id]?.mastered).length;
  const startedCount  = CURRICULUM.filter(t => progress[t.id]?.started && !progress[t.id]?.mastered).length;
  const overallPct    = Math.round((masteredCount / totalTopics) * 100);

  return (
    <div className="flex-1 p-8">
      <div className="max-w-3xl mx-auto flex flex-col gap-8">

        {/* Header */}
        <div>
          <p className="text-slate-500 text-xs uppercase tracking-widest">Your curriculum</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-100">Syllabus</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-400">
            This view tracks topic progress from Mentor Quick Practice. Teacher-made papers
            are in Question Banks; choose <span className="text-slate-200">Find papers</span>
            to see papers for a topic.
          </p>
        </div>

        {loading && <p className="text-slate-500 text-sm animate-pulse">Loading progress...</p>}
        {error   && <p className="text-red-400 text-sm">{error}</p>}

        {!loading && (
          <>
            {/* Overall progress bar */}
            <div className="flex flex-col gap-2 px-5 py-4 rounded-xl bg-indigo-900 border border-indigo-700">
              <div className="flex items-center justify-between text-sm">
                <span className="text-slate-300 font-medium">Overall completion</span>
                <span className="text-slate-100 font-bold">{overallPct}%</span>
              </div>
              <div className="w-full h-2 rounded-full bg-indigo-700">
                <div
                  className="h-2 rounded-full bg-green-500 transition-all duration-700"
                  style={{ width: `${overallPct}%` }}
                />
              </div>
              <div className="flex gap-4 text-xs text-slate-500 mt-0.5">
                <span><span className="text-green-400 font-semibold">{masteredCount}</span> mastered</span>
                <span><span className="text-blue-400 font-semibold">{startedCount}</span> in progress</span>
                <span><span className="text-slate-400 font-semibold">{totalTopics - masteredCount - startedCount}</span> remaining</span>
              </div>
            </div>

            {/* Per-category topic lists */}
            {CATEGORIES.map(category => {
              const topics = CURRICULUM.filter(t => t.category === category);
              return (
                <div key={category} className="flex flex-col gap-2">
                  <h2 className="text-slate-400 text-xs font-semibold uppercase tracking-widest px-1">
                    {category}
                  </h2>
                  {topics.map(topic => (
                    <TopicCard
                      key={topic.id}
                      topic={topic}
                      status={progress[topic.id]}
                      locked={isLocked(topic)}
                      onFindPapers={handleFindPapers}
                    />
                  ))}
                </div>
              );
            })}
          </>
        )}

      </div>
    </div>
  );
}
