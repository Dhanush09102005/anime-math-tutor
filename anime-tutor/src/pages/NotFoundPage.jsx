import { useNavigate } from "react-router-dom";

export default function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-indigo-950 text-slate-100 flex flex-col items-center justify-center gap-4">
      <div className="text-6xl">404</div>
      <p className="text-slate-400 text-sm">This page doesn't exist.</p>
      <button
        onClick={() => navigate("/")}
        className="px-5 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-slate-100
                   text-sm font-semibold transition-colors"
      >
        Go home
      </button>
    </div>
  );
}
