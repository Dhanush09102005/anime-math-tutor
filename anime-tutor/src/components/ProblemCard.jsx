import { useState } from "react";

export default function ProblemCard({ problem, onSubmit, onHint, loading, hint }) {
  const [answer, setAnswer] = useState("");

  function handleSubmit(e) {
    e.preventDefault();
    if (!answer.trim()) return;
    onSubmit(answer.trim());
    setAnswer("");
  }

  return (
    <div className="flex flex-col gap-4 px-6 py-5 rounded-lg bg-indigo-900 border border-indigo-700">
      {/* Mission label */}
      <div className="text-xs uppercase tracking-widest text-slate-500">
        Mission · {problem.topic.replace("_", " ")}
        {problem.generation_mode === "hybrid" && (
          <span className="ml-2 text-indigo-300 normal-case tracking-normal">
            AI-proposed · SymPy-verified
          </span>
        )}
      </div>

      {/* Problem text */}
      <p className="text-xl font-mono text-slate-100 tracking-wide">
        {problem.prompt_text}
      </p>

      {/* Answer form */}
      <form onSubmit={handleSubmit} className="flex gap-2 mt-1">
        <input
          type="text"
          value={answer}
          onChange={(e) => setAnswer(e.target.value)}
          placeholder={
            problem.answer_shape === "vector_or_matrix"
              ? "1, 2; 3, 4"
              : problem.answer_shape === "expression"
                ? "Enter an equivalent expression"
                : problem.answer_shape === "multi_value"
                  ? "x = 1, 2"
                  : "x = ?"
          }
          disabled={loading}
          className="flex-1 px-4 py-2 rounded bg-violet-950 border border-indigo-600
                     text-slate-100 placeholder-slate-500 font-mono
                     focus:outline-none focus:border-indigo-400
                     disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !answer.trim()}
          className="px-5 py-2 rounded bg-indigo-600 hover:bg-indigo-500
                     text-slate-100 font-semibold transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "..." : "Submit"}
        </button>
      </form>

      {/* Hint button */}
      <button
        onClick={onHint}
        disabled={loading}
        className="text-slate-500 hover:text-slate-300 text-sm underline
                   underline-offset-2 text-left transition-colors
                   disabled:opacity-40 disabled:cursor-not-allowed"
      >
        Ask for a hint
      </button>
      {hint && (
        <div className="rounded border border-amber-700/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-100">
          <span className="font-semibold">Hint: </span>{hint}
        </div>
      )}
    </div>
  );
}
