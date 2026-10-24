import { CHARACTERS, characterCards } from "../data/characters";

export default function CharacterSelect({ onSelect, loading }) {
  return (
    <div className="flex flex-col items-center gap-10">

      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-wide text-slate-100">
          Anime Math Tutor
        </h1>
        <p className="mt-2 text-slate-400 text-sm">
          Choose your sensei. They won't go easy on you.
        </p>
      </div>

      {/* Character cards grid */}
      <div className="grid grid-cols-2 gap-4 w-full max-w-2xl">
        {CHARACTERS.map((c) => {
          const cardImage = characterCards[c.id];

          return (
            <button
              key={c.id}
              onClick={() => c.active && onSelect(c.id)}
              disabled={!c.active || loading}
              className={`
                relative flex flex-col rounded-xl border overflow-hidden text-left
                transition-all duration-200
                ${c.active
                  ? "border-indigo-600 bg-indigo-900 hover:border-indigo-400 hover:scale-[1.02] cursor-pointer"
                  : "border-indigo-900 bg-violet-950 opacity-40 cursor-not-allowed"
                }
              `}
            >
              {/* Card image area */}
              <div className="w-full h-44 bg-indigo-700 flex items-center justify-center overflow-hidden">
                {cardImage ? (
                  <img
                    src={cardImage}
                    alt={c.name}
                    className="w-full h-full object-contain object-center"
                  />
                ) : (
                  <span className="text-slate-500 text-xs">
                    {c.active ? "Add image →\nsrc/assets/characters/kakashi.png" : "Coming soon"}
                  </span>
                )}
              </div>

              {/* Card text */}
              <div className="px-4 py-3 flex flex-col gap-0.5">
                <div className="text-slate-100 font-semibold text-sm">{c.name}</div>
                <div className="text-slate-400 text-xs">{c.title}</div>
                <div className="text-slate-500 text-xs mt-1 leading-snug">{c.flavor}</div>
              </div>

              {/* Loading overlay */}
              {loading && c.active && (
                <div className="absolute inset-0 bg-violet-950/60 flex items-center justify-center">
                  <span className="text-slate-300 text-sm animate-pulse">Starting session...</span>
                </div>
              )}

              {/* Coming soon badge */}
              {!c.active && (
                <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-indigo-700 text-slate-400 text-xs">
                  Soon
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
