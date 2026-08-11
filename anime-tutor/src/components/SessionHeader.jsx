// Maps difficulty to a mission rank label — Kakashi-flavored
function missionRank(difficulty) {
  if (difficulty <= 2) return { rank: "D", color: "text-slate-400" };
  if (difficulty <= 4) return { rank: "C", color: "text-green-400" };
  if (difficulty <= 6) return { rank: "B", color: "text-blue-400" };
  if (difficulty <= 8) return { rank: "A", color: "text-purple-400" };
  return { rank: "S", color: "text-yellow-400" };
}

export default function SessionHeader({ streak, difficulty, onQuit }) {
  const { rank, color } = missionRank(difficulty);

  return (
    <div className="flex items-center justify-between px-4 py-3 rounded-lg bg-slate-800 border border-slate-700">
      <div className="flex items-center gap-2">
        <span className="text-slate-400 text-xs uppercase tracking-widest">Sensei</span>
        <span className="text-slate-100 text-sm font-semibold">Kakashi Hatake</span>
      </div>

      <div className="flex items-center gap-4">
        <div className="text-center">
          <div className="text-slate-400 text-xs uppercase tracking-widest">Streak</div>
          <div className="text-slate-100 font-bold text-sm">{streak}</div>
        </div>
        <div className="text-center">
          <div className="text-slate-400 text-xs uppercase tracking-widest">Rank</div>
          <div className={`font-bold text-sm ${color}`}>{rank}</div>
        </div>
        <button
          onClick={onQuit}
          className="ml-2 text-slate-500 hover:text-red-400 text-xs underline
                     underline-offset-2 transition-colors"
        >
          quit
        </button>
      </div>
    </div>
  );
}
