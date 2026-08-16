import { useState, useRef, useEffect } from "react";

export default function ChatWindow({ messages, onSend, loading }) {
  const [input, setInput] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(e) {
    e.preventDefault();
    if (!input.trim() || loading) return;
    onSend(input.trim());
    setInput("");
  }

  return (
    <div className="flex flex-col flex-1 min-h-0 gap-3">

      {/* Scrolling message list */}
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-3 px-1 py-2"
      >
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-slate-500 text-sm text-center px-8">
            Say hi to get started — ask for a problem, ask a question, whatever's on your mind.
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="self-end max-w-[75%] px-4 py-2 rounded-lg bg-slate-700 text-slate-100 text-sm">
              {m.content}
            </div>
          ) : (
            <div
              key={i}
              className="self-start max-w-[75%] px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-200 text-sm leading-relaxed"
            >
              {m.content}
            </div>
          )
        )}

        {loading && (
          <div className="self-start px-4 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-500 text-sm">
            <span className="animate-pulse">...</span>
          </div>
        )}
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="flex gap-2 shrink-0">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          disabled={loading}
          className="flex-1 px-4 py-2 rounded bg-slate-900 border border-slate-600
                     text-slate-100 placeholder-slate-500
                     focus:outline-none focus:border-slate-400
                     disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || !input.trim()}
          className="px-5 py-2 rounded bg-slate-600 hover:bg-slate-500
                     text-slate-100 font-semibold transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
