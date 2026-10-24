import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { fetchSessionAttempts } from "../api/client";

const EVENT_LABELS = {
  correct_first_try:  { text: "Correct",          color: "text-green-400" },
  correct_streak:     { text: "Streak",            color: "text-green-300" },
  difficulty_milestone: { text: "Rank up",         color: "text-yellow-400" },
  comeback:           { text: "Comeback",          color: "text-blue-400" },
  incorrect:          { text: "Wrong",             color: "text-red-400" },
  repeated_mistake:   { text: "Repeated mistake",  color: "text-red-500" },
  frustration_warning:{ text: "Struggling",        color: "text-orange-400" },
  full_frustration:   { text: "Gave up (topic)",   color: "text-orange-600" },
  give_up_request:    { text: "Hint requested",    color: "text-slate-400" },
  topic_mastered:     { text: "Mastered",          color: "text-yellow-300" },
  not_serious:        { text: "Not serious",        color: "text-slate-500" },
};

export default function HistoryDetailPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [attempts, setAttempts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSessionAttempts(sessionId)
      .then(setAttempts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const correctCount = attempts.filter((attempt) => attempt.correct).length;
  const accuracy = attempts.length ? Math.round((correctCount / attempts.length) * 100) : 0;
  const topicStats = Object.values(
    attempts.reduce((stats, attempt) => {
      const topic = stats[attempt.topic] ?? { topic: attempt.topic, total: 0, correct: 0 };
      topic.total += 1;
      if (attempt.correct) topic.correct += 1;
      stats[attempt.topic] = topic;
      return stats;
    }, {}),
  );
  const reviewTopic = topicStats
    .filter((topic) => topic.total >= 2 && topic.correct < topic.total)
    .sort((a, b) => a.correct / a.total - b.correct / b.total)[0];

  return (
    <div className="flex-1 p-8">
      <div className="max-w-3xl mx-auto flex flex-col gap-6">

        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/history")}
            className="pill-btn text-slate-400 bg-violet-950 border border-indigo-700
                       hover:text-slate-100 hover:border-slate-500"
          >
            ← Back to history
          </button>
          <h1 className="text-xl font-semibold text-slate-100">Session detail</h1>
        </div>

        {loading && <p className="text-slate-500 text-sm animate-pulse">Loading attempts...</p>}
        {error   && <p className="text-red-400 text-sm">{error}</p>}

        {!loading && !error && attempts.length === 0 && (
          <p className="text-slate-500 text-sm">No attempts recorded for this session.</p>
        )}

        {!loading && !error && attempts.length > 0 && (
          <section className="grid gap-3 rounded-xl border border-indigo-700 bg-indigo-950/70 p-5 sm:grid-cols-3">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Session score</p>
              <p className="mt-1 text-xl font-semibold text-slate-100">{correctCount}/{attempts.length} correct</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Accuracy</p>
              <p className="mt-1 text-xl font-semibold text-slate-100">{accuracy}%</p>
            </div>
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-500">Review next</p>
              <p className="mt-1 text-xl font-semibold text-slate-100">
                {reviewTopic ? reviewTopic.topic.replace(/_/g, " ") : "Explore another topic"}
              </p>
            </div>
          </section>
        )}

        {!loading && attempts.length > 0 && (
          <div className="flex flex-col gap-2">
            {attempts.map((a, i) => {
              const label = EVENT_LABELS[a.event_category] ?? { text: a.event_category, color: "text-slate-400" };
              return (
                <div
                  key={a.id}
                  className="flex items-center justify-between px-4 py-3 rounded-lg
                             bg-indigo-900 border border-indigo-700 text-sm"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-slate-500 w-6 text-right">{i + 1}</span>
                    <span className="text-slate-300 font-mono">{a.problem_id}</span>
                    <span className="text-slate-500">{a.topic.replace(/_/g, " ")}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-slate-500 text-xs">D{a.difficulty}</span>
                    <span className={`text-xs font-semibold ${label.color}`}>{label.text}</span>
                    {a.mistake_type && (
                      <span className="text-slate-500 text-xs">{a.mistake_type}</span>
                    )}
                    <span className="text-indigo-600 text-xs">
                      {new Date(a.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

      </div>
    </div>
  );
}
