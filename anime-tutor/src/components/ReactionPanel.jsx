import { useEffect, useState } from "react";

function useTypewriter(text, speed = 18) {
  const [displayed, setDisplayed] = useState("");

  useEffect(() => {
    if (!text) return;
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed]);

  return displayed;
}

function TypewriterText({ text }) {
  const displayed = useTypewriter(text);

  return (
    <>
      {displayed}
      <span className="animate-pulse">▍</span>
    </>
  );
}

export default function ReactionPanel({ result, onNext, loading }) {
  const isCorrect    = result?.correct;

  const borderColor = isCorrect ? "border-green-700" : "border-red-800";
  const badge = isCorrect
    ? { text: "Correct", style: "bg-green-900/50 text-green-300" }
    : { text: "Wrong",   style: "bg-red-900/50 text-red-300"   };

  return (
    <div className={`flex flex-col gap-4 px-6 py-5 rounded-lg bg-slate-800 border ${borderColor}`}>

      {/* Badge + answer reveal */}
      <div className="flex items-center justify-between">
        <span className={`text-xs font-semibold px-2 py-0.5 rounded ${badge.style}`}>
          {badge.text}
        </span>
        {!isCorrect && result?.correct_answer && (
          <span className="text-slate-400 text-xs font-mono">
            Answer: <span className="text-slate-200">{result.correct_answer}</span>
          </span>
        )}
      </div>

      {/* Reaction text — typewriter */}
      <p className="text-slate-200 text-sm leading-relaxed min-h-[80px]">
        <TypewriterText key={result?.reaction ?? ""} text={result?.reaction ?? ""} />
      </p>

      {/* Next problem */}
      <button
        onClick={onNext}
        disabled={loading}
        className="mt-1 self-end px-5 py-2 rounded bg-slate-700 hover:bg-slate-600
                   text-slate-100 font-semibold text-sm transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {loading ? "Loading..." : "Next mission →"}
      </button>
    </div>
  );
}
