import { useNavigate } from "react-router-dom";

export default function TermsPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-indigo-950 text-slate-100 p-8">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">
        <button onClick={() => navigate(-1)}
          className="pill-btn text-slate-400 bg-violet-950 border border-indigo-700
                     hover:text-slate-100 hover:border-indigo-400 self-start">
          ← Back
        </button>
        <h1 className="text-3xl font-bold">Terms of Use</h1>
        <p className="text-slate-400 text-sm">Last updated: August 2026</p>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">Use of the service</h2>
          <p>Anime Math Tutor is a personal learning tool. You may use it for your own study. You may not attempt to scrape, reverse-engineer, or abuse the service.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">Character content</h2>
          <p>The anime character personas used in this app (Kakashi Hatake, Sukuna, Makima, Goku) are based on copyrighted fictional characters owned by their respective rights holders. This project is non-commercial and fan-made. If this app is ever made publicly available, original characters will replace the anime personas.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">No warranty</h2>
          <p>This service is provided as-is for educational purposes. Math problems are procedurally generated and while correctness is verified by SymPy, we make no guarantees about coverage or completeness of any topic.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">Account termination</h2>
          <p>You may delete your account at any time. We reserve the right to suspend accounts that abuse the service.</p>
        </section>
      </div>
    </div>
  );
}
