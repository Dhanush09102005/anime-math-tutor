import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchPaperAttempt, savePaperAnswers, submitPaperAttempt } from "../api/client";

function ErrorMessage({ children }) {
  return <div role="alert" className="rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-200">{children}</div>;
}

export default function PaperAttemptPage() {
  const { attemptId } = useParams();
  const navigate = useNavigate();
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [savingDraft, setSavingDraft] = useState(false);
  const [error, setError] = useState("");
  const draftTimer = useRef(null);

  useEffect(() => {
    let cancelled = false;
    fetchPaperAttempt(attemptId)
      .then((data) => {
        if (cancelled) return;
        setAttempt(data);
        setAnswers(data.answers?.length ? data.answers : Array(data.paper.questions.length).fill(""));
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attemptId]);

  useEffect(() => {
    if (!attempt || attempt.completed || submitting || answers.length !== attempt.paper.questions.length) return undefined;

    let cancelled = false;
    draftTimer.current = setTimeout(() => {
      setSavingDraft(true);
      savePaperAnswers(attemptId, answers)
        .catch((err) => {
          if (!cancelled) setError(err.message);
        })
        .finally(() => {
          if (!cancelled) setSavingDraft(false);
        });
    }, 400);

    return () => {
      cancelled = true;
      clearTimeout(draftTimer.current);
    };
  }, [answers, attempt, attemptId, submitting]);

  function updateAnswer(index, answer) {
    setAnswers((current) => current.map((value, itemIndex) => itemIndex === index ? answer : value));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    clearTimeout(draftTimer.current);
    if (answers.some((answer) => !answer.trim())) {
      setError("Answer every question before submitting your paper.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      const result = await submitPaperAttempt(attemptId, answers);
      setAttempt((current) => ({
        ...current,
        completed: true,
        score: result.score,
        correct_count: result.correct_count,
        results: result.results,
      }));
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return <main className="flex-1 p-8 text-center text-slate-300">Loading your paper…</main>;
  }

  if (error && !attempt) {
    return (
      <main className="flex-1 p-8">
        <div className="mx-auto max-w-2xl">
          <ErrorMessage>{error}</ErrorMessage>
          <Link className="mt-4 inline-block text-violet-300 underline" to="/question-banks">Back to Question Banks</Link>
        </div>
      </main>
    );
  }

  if (!attempt) return null;

  const { paper } = attempt;
  const results = attempt.results || [];

  return (
    <main className="flex-1 p-5 sm:p-8">
      <div className="mx-auto max-w-3xl">
        {attempt.completed ? (
          <section className="overflow-hidden rounded-3xl border border-violet-500/60 bg-gradient-to-br from-violet-900 via-indigo-900 to-fuchsia-950 shadow-2xl shadow-violet-950/50">
            <div className="p-7 text-center sm:p-10">
              <div className="text-5xl sm:text-6xl" aria-hidden="true">🎉 ✨ 🥳</div>
              <p className="mt-5 text-sm font-bold uppercase tracking-[0.25em] text-amber-200">Paper complete!</p>
              <h1 className="mt-2 text-3xl font-black text-white sm:text-4xl">YAAAH! You did it!</h1>
              <p className="mt-2 text-slate-200">{paper.title}</p>
              <div className="mx-auto mt-6 flex max-w-md items-center justify-center gap-4 rounded-2xl border border-white/15 bg-black/20 p-5">
                <div>
                  <p className="text-4xl font-black text-amber-300">{attempt.score}%</p>
                  <p className="mt-1 text-xs uppercase tracking-wider text-slate-300">Your score</p>
                </div>
                <div className="h-12 w-px bg-white/20" />
                <div>
                  <p className="text-2xl font-bold text-white">{attempt.correct_count}/{paper.questions.length}</p>
                  <p className="mt-1 text-xs uppercase tracking-wider text-slate-300">Correct answers</p>
                </div>
              </div>
              <div className="mt-6 flex flex-wrap justify-center gap-3">
                <button
                  onClick={() => navigate("/question-banks")}
                  className="rounded-lg bg-amber-300 px-5 py-2.5 text-sm font-bold text-indigo-950 hover:bg-amber-200"
                >
                  Back to Question Banks
                </button>
              </div>
            </div>
          </section>
        ) : (
          <header className="mb-6">
            <Link to="/question-banks" className="text-sm text-violet-300 hover:text-white">← Question Banks</Link>
            <p className="mt-5 text-xs uppercase tracking-[0.2em] text-violet-300">{paper.topic} · {paper.questions.length} questions</p>
            <h1 className="mt-2 text-3xl font-bold text-white">{paper.title}</h1>
            {paper.description && <p className="mt-2 text-sm text-slate-300">{paper.description}</p>}
          </header>
        )}

        {error && attempt && <div className="mb-5"><ErrorMessage>{error}</ErrorMessage></div>}

        {attempt.completed ? (
          <section className="mt-6 space-y-3">
            <h2 className="text-lg font-bold text-white">Answer review</h2>
            {results.map((result, index) => (
              <article key={index} className={`rounded-xl border p-4 ${result.correct ? "border-emerald-800 bg-emerald-950/30" : "border-rose-900 bg-rose-950/30"}`}>
                <p className="font-medium text-slate-100">{index + 1}. {result.prompt}</p>
                <p className="mt-2 text-sm text-slate-300">Your answer: <span className="text-white">{result.submitted_answer || "(blank)"}</span></p>
                {!result.correct && (
                  <p className="mt-1 text-sm text-emerald-300">Correct answer: {result.correct_answer || result.accepted_answers?.[0]}</p>
                )}
                <p className={`mt-2 text-xs font-bold uppercase ${result.correct ? "text-emerald-300" : "text-rose-300"}`}>
                  {result.correct ? "Correct ✓" : "Keep practicing"}
                </p>
              </article>
            ))}
          </section>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {paper.questions.map((question, index) => (
              <fieldset key={index} className="rounded-2xl border border-indigo-800 bg-indigo-900/50 p-5">
                <legend className="sr-only">Question {index + 1}</legend>
                <p className="font-medium leading-relaxed text-white">
                  <span className="mr-2 text-violet-300">{index + 1}.</span>{question.prompt}
                </p>
                {question.question_type === "multiple_choice" ? (
                  <div className="mt-4 grid gap-2">
                    {question.options.map((option) => (
                      <label key={option} className={`flex cursor-pointer items-center gap-3 rounded-lg border px-3 py-2.5 text-sm transition ${answers[index] === option ? "border-violet-500 bg-violet-950 text-white" : "border-indigo-800 bg-indigo-950/50 text-slate-300 hover:border-indigo-600"}`}>
                        <input
                          type="radio"
                          name={`question-${index}`}
                          value={option}
                          checked={answers[index] === option}
                          onChange={(event) => updateAnswer(index, event.target.value)}
                          className="accent-violet-500"
                        />
                        {option}
                      </label>
                    ))}
                  </div>
                ) : (
                  <input
                    type="text"
                    value={answers[index] || ""}
                    onChange={(event) => updateAnswer(index, event.target.value)}
                    placeholder="Type your answer"
                    className="mt-4 w-full rounded-lg border border-indigo-700 bg-indigo-950 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-400"
                  />
                )}
              </fieldset>
            ))}
            <button
              type="submit"
              disabled={submitting || savingDraft}
              className="w-full rounded-xl bg-violet-700 px-5 py-3 font-bold text-white hover:bg-violet-600 disabled:cursor-wait disabled:opacity-60"
            >
              {submitting ? "Checking your answers…" : savingDraft ? "Saving answers…" : "Submit paper"}
            </button>
            <p className="text-center text-xs text-slate-500">
              {savingDraft ? "Saving your draft…" : "Your answers are saved automatically as you work."}
            </p>
            <p className="text-center text-xs text-slate-500">Answers are checked when you submit. Short answers use exact text matching (ignoring capitalization and extra spaces).</p>
          </form>
        )}
      </div>
    </main>
  );
}
