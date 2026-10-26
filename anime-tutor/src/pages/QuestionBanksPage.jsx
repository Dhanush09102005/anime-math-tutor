import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { createPaperAttempt, fetchQuestionPapers } from "../api/client";

const TOPIC_NAMES = {
  numbers: "Playing with Numbers",
  linear_equations: "Linear Equations",
  logarithms: "Logarithms",
  sets_relations: "Sets & Relations",
  quadratic_equations: "Quadratic Equations",
  progressions: "Progressions",
  binomial_theorem: "Binomial Theorem",
  complex_numbers: "Complex Numbers",
  trigonometry: "Trigonometry",
  matrices_determinants: "Matrices & Determinants",
  linear_algebra: "Linear Algebra (Eigenvalues)",
  coordinate_geometry: "Coordinate Geometry",
  vectors_3d: "Vectors & 3D Geometry",
  calculus: "Derivatives & Integrals",
  probability: "P&C and Probability",
  statistics: "Statistics",
};

export default function QuestionBanksPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [startingId, setStartingId] = useState(null);
  const [error, setError] = useState("");
  const topicFilter = location.state?.topic || "";

  const loadPapers = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setPapers(await fetchQuestionPapers());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchQuestionPapers()
      .then((data) => {
        if (!cancelled) setPapers(data);
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
  }, []);

  const visiblePapers = useMemo(() => {
    if (!topicFilter) return papers;
    const topicName = TOPIC_NAMES[topicFilter] || topicFilter.replaceAll("_", " ");
    return papers.filter((paper) =>
      [paper.topic, paper.topic.replaceAll("_", " ")].some(
        (topic) => topic.toLowerCase() === topicName.toLowerCase()
          || topic.toLowerCase() === topicFilter.toLowerCase(),
      ),
    );
  }, [papers, topicFilter]);

  async function openPaper(paper) {
    setStartingId(paper.id);
    setError("");
    try {
      const { attempt_id: attemptId } = await createPaperAttempt(paper.id);
      navigate(`/question-banks/${paper.id}/attempts/${attemptId}`);
    } catch (err) {
      setError(err.message);
      setStartingId(null);
    }
  }

  return (
    <main className="flex-1 p-6 sm:p-8">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <p className="text-xs uppercase tracking-[0.2em] text-violet-300">Teacher-made practice</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Question Banks</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
            Take papers added by your teachers, see your score as soon as you submit,
            and come back to any paper you have already started.
          </p>
          {topicFilter && (
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <span className="rounded-full border border-indigo-700 bg-indigo-900 px-3 py-1 text-sm text-indigo-200">
                {TOPIC_NAMES[topicFilter] || topicFilter.replaceAll("_", " ")}
              </span>
              <button
                onClick={() => navigate("/question-banks", { replace: true })}
                className="text-sm text-violet-300 underline hover:text-white"
              >
                Show all papers
              </button>
            </div>
          )}
        </header>

        {error && (
          <div role="alert" className="mb-5 rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-200">
            {error}
            {!loading && (
              <button onClick={loadPapers} className="ml-3 underline hover:text-white">
                Try again
              </button>
            )}
          </div>
        )}

        {loading ? (
          <p className="text-slate-400">Loading papers…</p>
        ) : visiblePapers.length === 0 ? (
          <section className="rounded-2xl border border-indigo-800 bg-indigo-900/50 p-8 text-center">
            <div className="text-4xl" aria-hidden="true">📚</div>
            <h2 className="mt-3 text-xl font-semibold text-white">
              {topicFilter ? "No papers for this topic yet" : "No papers have been added yet"}
            </h2>
            <p className="mx-auto mt-2 max-w-lg text-sm text-slate-300">
              {topicFilter
                ? "Try all papers, or check back after your teacher adds a paper for this topic."
                : "Your teacher can add question papers from the Admin page. They will appear here as soon as they are published."}
            </p>
            {topicFilter && (
              <button
                onClick={() => navigate("/question-banks", { replace: true })}
                className="mt-5 rounded-lg bg-violet-700 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-600"
              >
                Browse all papers
              </button>
            )}
          </section>
        ) : (
          <div className="grid gap-4 md:grid-cols-2">
            {visiblePapers.map((paper) => {
              const inProgress = Boolean(paper.in_progress_attempt_id);
              return (
                <article key={paper.id} className="rounded-2xl border border-indigo-800 bg-indigo-900/60 p-5 shadow-lg shadow-black/10">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <span className="rounded-full bg-violet-900 px-2.5 py-1 text-xs font-medium text-violet-200">
                        {paper.topic}
                      </span>
                      <h2 className="mt-3 text-xl font-semibold text-white">{paper.title}</h2>
                    </div>
                    {paper.best_score !== null && (
                      <span className="rounded-lg bg-emerald-950 px-3 py-1.5 text-sm font-semibold text-emerald-300">
                        Best: {paper.best_score}%
                      </span>
                    )}
                  </div>
                  {paper.description && <p className="mt-2 text-sm text-slate-300">{paper.description}</p>}
                  <div className="mt-4 flex flex-wrap gap-x-4 gap-y-1 text-xs text-slate-400">
                    <span>{paper.question_count} questions</span>
                    <span>{paper.completed_count} completed {paper.completed_count === 1 ? "attempt" : "attempts"}</span>
                    {inProgress && <span className="text-amber-300">In progress</span>}
                  </div>
                  <button
                    onClick={() => openPaper(paper)}
                    disabled={startingId !== null}
                    className="mt-5 w-full rounded-lg bg-violet-700 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-violet-600 disabled:cursor-wait disabled:opacity-60"
                  >
                    {startingId === paper.id
                      ? "Opening…"
                      : inProgress
                        ? "Continue paper →"
                        : paper.completed_count
                          ? "Try again →"
                          : "Start paper →"}
                  </button>
                </article>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
