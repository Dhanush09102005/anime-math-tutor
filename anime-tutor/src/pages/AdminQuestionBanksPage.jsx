import { useCallback, useEffect, useState } from "react";
import { createQuestionPaper, fetchStudentPaperProgress } from "../api/client";

const blankQuestion = () => ({
  prompt: "",
  question_type: "multiple_choice",
  options: "",
  accepted_answers: "",
});

export default function AdminQuestionBanksPage() {
  const [paper, setPaper] = useState({ title: "", description: "", topic: "", questions: [blankQuestion()] });
  const [progress, setProgress] = useState([]);
  const [loadingProgress, setLoadingProgress] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadProgress = useCallback(async () => {
    setLoadingProgress(true);
    try {
      setProgress(await fetchStudentPaperProgress());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingProgress(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetchStudentPaperProgress()
      .then((data) => {
        if (!cancelled) setProgress(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoadingProgress(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  function updatePaper(field, value) {
    setPaper((current) => ({ ...current, [field]: value }));
  }

  function updateQuestion(index, field, value) {
    setPaper((current) => ({
      ...current,
      questions: current.questions.map((question, questionIndex) =>
        questionIndex === index ? { ...question, [field]: value } : question,
      ),
    }));
  }

  function removeQuestion(index) {
    setPaper((current) => ({
      ...current,
      questions: current.questions.filter((_, questionIndex) => questionIndex !== index),
    }));
  }

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    setNotice("");
    setSaving(true);
    try {
      const payload = {
        title: paper.title,
        description: paper.description,
        topic: paper.topic,
        questions: paper.questions.map((question) => ({
          prompt: question.prompt,
          question_type: question.question_type,
          options: question.question_type === "multiple_choice"
            ? question.options.split("\n").map((option) => option.trim()).filter(Boolean)
            : [],
          accepted_answers: question.accepted_answers.split("\n").map((answer) => answer.trim()).filter(Boolean),
        })),
      };
      const created = await createQuestionPaper(payload);
      setNotice(`"${created.title}" is now available to students.`);
      setPaper({ title: "", description: "", topic: "", questions: [blankQuestion()] });
      await loadProgress();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="flex-1 p-6 sm:p-8">
      <div className="mx-auto max-w-5xl space-y-10">
        <header>
          <p className="text-xs uppercase tracking-[0.2em] text-amber-300">Teacher controls</p>
          <h1 className="mt-2 text-3xl font-bold text-white">Question Bank Admin</h1>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
            Create a paper below. It is published to students immediately. Their attempts,
            completion status, and scores appear in the progress table.
          </p>
        </header>

        {error && <div role="alert" className="rounded-xl border border-red-800 bg-red-950/50 p-4 text-sm text-red-200">{error}</div>}
        {notice && <div role="status" className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4 text-sm text-emerald-200">{notice}</div>}

        <section className="rounded-2xl border border-indigo-800 bg-indigo-900/40 p-5 sm:p-7">
          <h2 className="text-xl font-bold text-white">Add a paper</h2>
          <p className="mt-1 text-sm text-slate-400">
            Grading ignores capitalization and extra spaces, but otherwise matches answer text exactly.
          </p>
          <form onSubmit={handleCreate} className="mt-6 space-y-5">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="text-sm font-medium text-slate-200">
                Paper title
                <input
                  required
                  maxLength={160}
                  value={paper.title}
                  onChange={(event) => updatePaper("title", event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-950 px-3 py-2 text-white outline-none focus:border-violet-400"
                  placeholder="e.g. Algebra Checkpoint 1"
                />
              </label>
              <label className="text-sm font-medium text-slate-200">
                Topic
                <input
                  required
                  maxLength={100}
                  value={paper.topic}
                  onChange={(event) => updatePaper("topic", event.target.value)}
                  className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-950 px-3 py-2 text-white outline-none focus:border-violet-400"
                  placeholder="e.g. Linear Equations"
                />
              </label>
            </div>
            <label className="block text-sm font-medium text-slate-200">
              Description <span className="font-normal text-slate-500">(optional)</span>
              <textarea
                rows={2}
                maxLength={1000}
                value={paper.description}
                onChange={(event) => updatePaper("description", event.target.value)}
                className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-950 px-3 py-2 text-white outline-none focus:border-violet-400"
                placeholder="Instructions or a short description for students"
              />
            </label>

            <div className="space-y-4">
              {paper.questions.map((question, index) => (
                <fieldset key={index} className="rounded-xl border border-indigo-800 bg-indigo-950/60 p-4">
                  <legend className="px-2 text-sm font-semibold text-violet-200">Question {index + 1}</legend>
                  <div className="flex flex-col gap-4">
                    <label className="text-sm font-medium text-slate-200">
                      Question text
                      <textarea
                        required
                        maxLength={5000}
                        rows={3}
                        value={question.prompt}
                        onChange={(event) => updateQuestion(index, "prompt", event.target.value)}
                        className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-900 px-3 py-2 text-white outline-none focus:border-violet-400"
                        placeholder="Enter the question"
                      />
                    </label>
                    <label className="max-w-xs text-sm font-medium text-slate-200">
                      Answer format
                      <select
                        value={question.question_type}
                        onChange={(event) => updateQuestion(index, "question_type", event.target.value)}
                        className="mt-1.5 block w-full rounded-lg border border-indigo-700 bg-indigo-900 px-3 py-2 text-white outline-none focus:border-violet-400"
                      >
                        <option value="multiple_choice">Multiple choice</option>
                        <option value="short_answer">Short answer</option>
                      </select>
                    </label>
                    {question.question_type === "multiple_choice" && (
                      <label className="text-sm font-medium text-slate-200">
                        Options <span className="font-normal text-slate-500">(one per line; at least two)</span>
                        <textarea
                          required
                          rows={4}
                          value={question.options}
                          onChange={(event) => updateQuestion(index, "options", event.target.value)}
                          className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-900 px-3 py-2 text-white outline-none focus:border-violet-400"
                          placeholder={"3\n4\n5\n6"}
                        />
                      </label>
                    )}
                    <label className="text-sm font-medium text-slate-200">
                      {question.question_type === "multiple_choice" ? "Correct option" : "Accepted answer(s)"}
                      <span className="ml-1 font-normal text-slate-500">
                        {question.question_type === "multiple_choice" ? "(must match an option; case-insensitive)" : "(one per line; alternatives are allowed)"}
                      </span>
                      <textarea
                        required
                        rows={question.question_type === "multiple_choice" ? 1 : 2}
                        value={question.accepted_answers}
                        onChange={(event) => updateQuestion(index, "accepted_answers", event.target.value)}
                        className="mt-1.5 w-full rounded-lg border border-indigo-700 bg-indigo-900 px-3 py-2 text-white outline-none focus:border-violet-400"
                        placeholder={question.question_type === "multiple_choice" ? "Enter the correct option" : "One accepted answer per line"}
                      />
                    </label>
                    {paper.questions.length > 1 && (
                      <button type="button" onClick={() => removeQuestion(index)} className="self-start text-sm text-rose-300 hover:text-rose-200">
                        Remove question
                      </button>
                    )}
                  </div>
                </fieldset>
              ))}
            </div>

            <div className="flex flex-wrap gap-3">
              <button
                type="button"
                onClick={() => setPaper((current) => ({ ...current, questions: [...current.questions, blankQuestion()] }))}
                disabled={paper.questions.length >= 100}
                className="rounded-lg border border-indigo-600 px-4 py-2 text-sm font-semibold text-indigo-200 hover:bg-indigo-900 disabled:opacity-50"
              >
                + Add question
              </button>
              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-violet-700 px-5 py-2 text-sm font-bold text-white hover:bg-violet-600 disabled:cursor-wait disabled:opacity-60"
              >
                {saving ? "Publishing…" : "Publish paper"}
              </button>
            </div>
          </form>
        </section>

        <section>
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-violet-300">Student activity</p>
              <h2 className="mt-1 text-2xl font-bold text-white">Paper progress</h2>
            </div>
            <button
              onClick={loadProgress}
              disabled={loadingProgress}
              className="rounded-lg border border-indigo-700 px-3 py-2 text-sm text-slate-200 hover:bg-indigo-900 disabled:opacity-50"
            >
              Refresh
            </button>
          </div>
          <div className="mt-4 overflow-x-auto rounded-xl border border-indigo-800">
            {loadingProgress ? (
              <p className="p-5 text-sm text-slate-400">Loading student progress…</p>
            ) : progress.length === 0 ? (
              <p className="p-5 text-sm text-slate-400">No student attempts yet. Attempts will appear here once students start a paper.</p>
            ) : (
              <table className="w-full min-w-[700px] border-collapse text-left text-sm">
                <thead className="bg-indigo-900 text-xs uppercase tracking-wide text-slate-300">
                  <tr>
                    <th className="px-4 py-3">Student</th>
                    <th className="px-4 py-3">Paper</th>
                    <th className="px-4 py-3">Result</th>
                    <th className="px-4 py-3">Started</th>
                    <th className="px-4 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-indigo-900 bg-indigo-950/60">
                  {progress.map((row) => (
                    <tr key={row.attempt_id}>
                      <td className="px-4 py-3 text-slate-200">{row.student_email}</td>
                      <td className="px-4 py-3 text-slate-200">{row.paper_title}</td>
                      <td className="px-4 py-3 text-slate-200">
                        {row.completed_at ? `${row.score}% (${row.correct_count}/${row.question_count})` : "—"}
                      </td>
                      <td className="px-4 py-3 text-slate-400">{new Date(row.started_at).toLocaleString()}</td>
                      <td className="px-4 py-3">
                        <span className={`rounded-full px-2 py-1 text-xs font-medium ${row.completed_at ? "bg-emerald-950 text-emerald-300" : "bg-amber-950 text-amber-300"}`}>
                          {row.completed_at ? "Completed" : "In progress"}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
