import { kakashiMoods } from "../assets/kakashi/index.js";

export default function CharacterPanel({ mood = "default" }) {
  // Use the mood image if it exists, fall back to default, fall back to null
  const image = kakashiMoods[mood] ?? kakashiMoods["default"] ?? null;

  return (
    <div className="relative w-1/2 h-screen bg-slate-900 shrink-0 overflow-hidden">
      {image ? (
        <img
          src={image}
          alt={`Kakashi — ${mood}`}
          className="w-full h-full object-cover object-top"
        />
      ) : (
        // Placeholder until images are added
        <div className="w-full h-full flex flex-col items-center justify-center gap-3">
          <div className="text-slate-600 text-6xl">🥷</div>
          <div className="text-slate-600 text-xs text-center px-8 leading-relaxed">
            Drop mood images in<br />
            <span className="font-mono text-slate-500">src/assets/kakashi/</span>
          </div>
        </div>
      )}

      {/* Subtle gradient at the bottom so text on right side doesn't clash */}
      <div className="absolute inset-0 bg-gradient-to-r from-transparent to-slate-950/30 pointer-events-none" />
    </div>
  );
}
