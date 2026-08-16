const MODES = [
  {
    id: "qna",
    name: "Quick Practice",
    tagline: "Problem, answer, reaction. Repeat.",
    description:
      "Straight to the point — solve problems back to back, get an instant in-character reaction, watch your streak and rank climb.",
  },
  {
    id: "chat",
    name: "Just Talk",
    tagline: "An actual conversation.",
    description:
      "Talk it through instead. Ask why, ask for a different explanation, go on tangents — your sensei teaches, not just grades.",
  },
];

export default function ModeSelect({ onSelect, onBack, loading }) {
  return (
    <div className="flex flex-col items-center gap-10 w-full max-w-2xl">

      <div className="w-full flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-slate-500 hover:text-slate-300 text-xs tracking-wide transition-colors"
        >
          ‹ change sensei
        </button>
      </div>

      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-wide text-slate-100">
          How do you want to learn?
        </h1>
        <p className="mt-2 text-slate-400 text-sm">
          Switch anytime by starting a new session.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => onSelect(m.id)}
            disabled={loading}
            className="relative flex flex-col gap-2 rounded-xl border border-slate-600 bg-slate-800
                       px-6 py-6 text-left transition-all duration-200
                       hover:border-slate-400 hover:scale-[1.02] cursor-pointer
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <div className="text-slate-100 text-lg font-semibold">{m.name}</div>
            <div className="text-slate-400 text-xs uppercase tracking-widest">{m.tagline}</div>
            <div className="text-slate-500 text-sm leading-relaxed mt-1">{m.description}</div>

            {loading && (
              <div className="absolute inset-0 bg-slate-900/60 rounded-xl flex items-center justify-center">
                <span className="text-slate-300 text-sm animate-pulse">Starting...</span>
              </div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
