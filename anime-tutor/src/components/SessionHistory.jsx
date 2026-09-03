import { CHARACTERS } from "../data/characters";

function formatTopic(topic) {
  return topic.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function SessionHistory({ sessions, loading, error, onBack }) {
  return (
    <div className="w-full max-w-3xl flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-slate-500 text-xs uppercase tracking-[0.25em]">Your progress</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-100">Session history</h1>
        </div>
        <button
          type="button"
          onClick={onBack}
          className="px-3 py-2 rounded border border-slate-600 text-slate-300 text-sm
                     hover:border-slate-400 hover:text-white transition-colors"
        >
          Back
        </button>
      </div>

      {error && (
        <div className="px-4 py-3 rounded border border-red-700 bg-red-950/40 text-red-300 text-sm">
          {error}
        </div>
      )}

      {loading && (
        <div className="py-12 text-center text-slate-500 text-sm animate-pulse">
          Loading your sessions...
        </div>
      )}

      {!loading && !error && sessions.length === 0 && (
        <div className="py-12 text-center rounded-lg border border-slate-800 bg-slate-900/60">
          <p className="text-slate-300">No sessions yet.</p>
          <p className="mt-1 text-slate-500 text-sm">Complete a practice session and it will appear here.</p>
        </div>
      )}

      {!loading && !error && sessions.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-700 bg-slate-900/70">
          {sessions.map((session) => {
            const character = CHARACTERS.find((item) => item.id === session.persona_id);
            const accuracy = session.attempt_count
              ? Math.round((session.correct_count / session.attempt_count) * 100)
              : 0;

            return (
              <div
                key={session.session_id}
                className="grid grid-cols-[1fr_auto] gap-4 px-5 py-4 border-b border-slate-800 last:border-b-0"
              >
                <div className="min-w-0">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <h2 className="text-slate-100 font-medium">
                      {character?.name ?? session.persona_id}
                    </h2>
                    <span className="text-slate-500 text-xs">{formatTopic(session.topic)}</span>
                  </div>
                  <p className="mt-1 text-slate-500 text-xs">{formatDate(session.created_at)}</p>
                </div>
                <div className="text-right text-xs whitespace-nowrap">
                  <div className="text-slate-300">{session.attempt_count} attempts</div>
                  <div className="mt-1 text-slate-500">
                    {accuracy}% correct · streak {session.streak}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
