import { CHARACTERS } from "../data/characters";

// Universal difficulty label — no longer Naruto-specific rank letters,
// since this now needs to make sense for every persona, not just Kakashi.
function difficultyLabel(difficulty) {
  if (difficulty <= 2) return { label: "Novice", color: "text-slate-400" };
  if (difficulty <= 4) return { label: "Intermediate", color: "text-green-400" };
  if (difficulty <= 6) return { label: "Advanced", color: "text-blue-400" };
  if (difficulty <= 8) return { label: "Expert", color: "text-purple-400" };
  return { label: "Master", color: "text-yellow-400" };
}

export default function SessionHeader({ personaId, streak, difficulty, onQuit, userEmail, onLogout }) {
  const { label, color } = difficultyLabel(difficulty);
  const character = CHARACTERS.find((c) => c.id === personaId);
  const displayName = character?.name ?? "Sensei";
  const displayTitle = character?.title ?? "";

  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-indigo-900 border border-indigo-700">
      <div className="flex items-center gap-2">
        <span className="text-slate-400 text-xs uppercase tracking-widest">
          {displayTitle || "Sensei"}
        </span>
        <span className="text-slate-100 text-sm font-semibold">{displayName}</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-slate-400 text-xs uppercase tracking-widest">Streak</div>
          <div className="text-slate-100 font-bold text-sm">{streak}</div>
        </div>
        <div className="text-center">
          <div className="text-slate-400 text-xs uppercase tracking-widest">Level</div>
          <div className={`font-bold text-sm ${color}`}>{label}</div>
        </div>
        <button
          onClick={onQuit}
          className="pill-btn ml-2 text-slate-400 bg-violet-950 border border-indigo-700
                     hover:text-red-300 hover:border-red-800 hover:bg-red-950/30"
        >
          Quit
        </button>
        {onLogout && (
          <button
            onClick={onLogout}
            title={userEmail ?? undefined}
            className="pill-btn text-slate-500 bg-violet-950 border border-indigo-700
                       hover:text-slate-100 hover:border-indigo-400"
          >
            Log out
          </button>
        )}
      </div>
    </div>
  );
}
