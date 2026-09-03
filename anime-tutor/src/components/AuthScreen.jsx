import { useState } from "react";
import { loginUser, registerUser, googleLoginUrl } from "../api/client";

// Shown before CharacterSelect — gates the whole app behind a logged-in
// user, since every session/problem/submit/chat call now requires auth.
export default function AuthScreen({ onAuthenticated, loading, setLoading }) {
  const [mode, setMode] = useState("login"); // "login" | "register"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const user = mode === "login"
        ? await loginUser(email, password)
        : await registerUser(email, password);
      onAuthenticated(user);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleGoogleClick() {
    // Full page navigation, not a fetch — Google's OAuth flow needs an
    // actual browser redirect, not an XHR/fetch request.
    window.location.href = googleLoginUrl();
  }

  return (
    <div className="flex flex-col items-center gap-8 w-full max-w-sm">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-wide text-slate-100">
          Anime Math Tutor
        </h1>
        <p className="mt-2 text-slate-400 text-sm">
          {mode === "login" ? "Welcome back." : "Create an account to start."}
        </p>
      </div>

      {error && (
        <div className="w-full px-4 py-2 bg-red-900/50 border border-red-700
                        rounded text-red-300 text-sm">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="w-full flex flex-col gap-3">
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
          className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600
                     text-slate-100 placeholder-slate-500 focus:outline-none
                     focus:border-slate-400"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={8}
          className="w-full px-4 py-2 rounded-lg bg-slate-800 border border-slate-600
                     text-slate-100 placeholder-slate-500 focus:outline-none
                     focus:border-slate-400"
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full px-4 py-2 rounded-lg bg-slate-100 text-slate-900
                     font-semibold hover:bg-white transition-colors disabled:opacity-50
                     disabled:cursor-not-allowed"
        >
          {loading ? "..." : mode === "login" ? "Log in" : "Register"}
        </button>
      </form>

      <div className="w-full flex items-center gap-3">
        <div className="flex-1 h-px bg-slate-700" />
        <span className="text-slate-500 text-xs">or</span>
        <div className="flex-1 h-px bg-slate-700" />
      </div>

      <button
        onClick={handleGoogleClick}
        disabled={loading}
        className="w-full px-4 py-2 rounded-lg border border-slate-600 text-slate-200
                   hover:border-slate-400 transition-colors disabled:opacity-50
                   disabled:cursor-not-allowed"
      >
        Continue with Google
      </button>

      <button
        onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); }}
        className="text-slate-400 text-sm hover:text-slate-200 transition-colors"
      >
        {mode === "login"
          ? "Don't have an account? Register"
          : "Already have an account? Log in"}
      </button>
    </div>
  );
}
