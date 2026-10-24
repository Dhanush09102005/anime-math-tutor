import { useEffect, useState } from "react";
import { fetchAnalytics } from "../api/client";

function AccuracyBar({ value }) {
  const color =
    value >= 80 ? "bg-green-500" :
    value >= 50 ? "bg-yellow-500" :
    "bg-red-500";
  return (
    <div className="w-full h-1.5 rounded-full bg-indigo-700">
      <div
        className={`h-1.5 rounded-full ${color} transition-all duration-500`}
        style={{ width: `${value}%` }}
      />
    </div>
  );
}

function DifficultyBadge({ value }) {
  const rank =
    value >= 9 ? { label: "S", color: "text-yellow-400 border-yellow-700" } :
    value >= 7 ? { label: "A", color: "text-purple-400 border-purple-700" } :
    value >= 5 ? { label: "B", color: "text-blue-400 border-blue-700" } :
    value >= 3 ? { label: "C", color: "text-green-400 border-green-700" } :
                 { label: "D", color: "text-slate-400 border-indigo-600" };
  return (
    <span className={`text-xs font-bold px-1.5 py-0.5 rounded border ${rank.color}`}>
      {rank.label}
    </span>
  );
}

export default function DashboardPage() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    fetchAnalytics()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex-1 p-8">
      <div className="max-w-4xl mx-auto flex flex-col gap-8">

        {/* Header */}
        <div>
          <p className="text-slate-500 text-xs uppercase tracking-widest">Your stats</p>
          <h1 className="mt-1 text-3xl font-bold text-slate-100">Dashboard</h1>
        </div>

        {loading && (
          <p className="text-slate-500 text-sm animate-pulse">Loading your stats...</p>
        )}
        {error && (
          <p className="text-red-400 text-sm">{error}</p>
        )}

        {data && (
          <>
            {/* Overview cards */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: "Total attempts",  value: data.total_attempts },
                { label: "Correct answers", value: data.total_correct },
                { label: "Overall accuracy", value: `${data.overall_accuracy}%` },
              ].map(card => (
                <div
                  key={card.label}
                  className="flex flex-col gap-1 px-5 py-4 rounded-xl bg-indigo-900
                             border border-indigo-700"
                >
                  <span className="text-slate-400 text-xs uppercase tracking-widest">
                    {card.label}
                  </span>
                  <span className="text-3xl font-bold text-slate-100">{card.value}</span>
                </div>
              ))}
            </div>

            {/* Per-topic breakdown */}
            {data.topics.length === 0 ? (
              <div className="py-16 text-center rounded-xl border border-indigo-900 bg-violet-950/50">
                <p className="text-slate-400">No attempts yet.</p>
                <p className="mt-1 text-slate-500 text-sm">
                  Complete a Quick Practice session and your stats will appear here.
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                <h2 className="text-slate-300 text-sm font-semibold uppercase tracking-widest mb-1">
                  By topic
                </h2>
                {data.topics.map(t => (
                  <div
                    key={t.topic}
                    className="flex flex-col gap-2 px-5 py-4 rounded-xl bg-indigo-900
                               border border-indigo-700"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <DifficultyBadge value={t.best_difficulty} />
                        <span className="text-slate-100 text-sm font-medium capitalize">
                          {t.topic.replace(/_/g, " ")}
                        </span>
                      </div>
                      <div className="flex items-center gap-4 text-xs text-slate-400">
                        <span>{t.correct_attempts}/{t.total_attempts} correct</span>
                        <span className="font-semibold text-slate-200">{t.accuracy}%</span>
                      </div>
                    </div>
                    <AccuracyBar value={t.accuracy} />
                  </div>
                ))}
              </div>
            )}
          </>
        )}

      </div>
    </div>
  );
}
