import { useNavigate } from "react-router-dom";

export default function PrivacyPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-indigo-950 text-slate-100 p-8">
      <div className="max-w-2xl mx-auto flex flex-col gap-6">
        <button onClick={() => navigate(-1)}
          className="pill-btn text-slate-400 bg-violet-950 border border-indigo-700
                     hover:text-slate-100 hover:border-indigo-400 self-start">
          ← Back
        </button>
        <h1 className="text-3xl font-bold">Privacy Policy</h1>
        <p className="text-slate-400 text-sm">Last updated: August 2026</p>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">What we collect</h2>
          <p>When you register, we store your email address and a hashed (bcrypt) password, or your Google account identifier if you sign in with Google. We never store your raw password.</p>
          <p>During a session, we log which problems you attempted, whether you answered correctly, and the difficulty level — this forms your session history.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">What we don't collect</h2>
          <p>We don't collect payment information, real names, phone numbers, or location data. We don't run third-party analytics or advertising trackers.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">How we use your data</h2>
          <p>Your session history is used solely to show you your own past performance. We don't share it with anyone, sell it, or use it to train models.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">Deleting your data</h2>
          <p>You can delete your account and all associated data at any time from the Account page. Deletion is permanent and immediate.</p>
        </section>

        <section className="flex flex-col gap-3 text-slate-300 text-sm leading-relaxed">
          <h2 className="text-slate-100 font-semibold text-base">Contact</h2>
          <p>Questions about this policy? Reach out via the project's GitHub repository.</p>
        </section>
      </div>
    </div>
  );
}
