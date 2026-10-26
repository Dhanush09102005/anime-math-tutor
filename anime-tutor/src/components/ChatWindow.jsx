import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

function renderMath(text) {
  return text
    .replaceAll("\\[", "$$")
    .replaceAll("\\]", "$$")
    .replaceAll("\\(", "$")
    .replaceAll("\\)", "$");
}

export default function ChatWindow({ messages, onSend, loading, topic }) {
  const [input, setInput]   = useState("");
  const [file, setFile]     = useState(null);   // File object or null
  const scrollRef           = useRef(null);
  const fileInputRef        = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, loading]);

  function handleSubmit(e) {
    e.preventDefault();
    if ((!input.trim() && !file) || loading) return;
    onSend(input.trim(), file);
    setInput("");
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  function handleFileChange(e) {
    setFile(e.target.files[0] ?? null);
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
            {topic && topic !== "general" ? (
              <span>
                Syllabus focus: <span className="text-slate-300">{topic.replaceAll("_", " ")}</span>.
                Ask a question or share a problem, and your sensei will help you work through it.
              </span>
            ) : (
              "Type a problem, paste a question, or upload an image or PDF — your sensei will walk you through it."
            )}
          </div>
        )}

        {messages.map((m, i) =>
          m.role === "user" ? (
            <div key={i} className="self-end max-w-[75%] flex flex-col items-end gap-1">
              {m.fileName && (
                <span className="text-xs text-slate-400 px-2">📎 {m.fileName}</span>
              )}
              <div className="px-4 py-2 rounded-lg bg-indigo-700 text-slate-100 text-sm">
                {m.content || <span className="italic text-slate-400">(file only)</span>}
              </div>
            </div>
          ) : (
            <div
              key={i}
              className="self-start max-w-[75%] px-4 py-2 rounded-lg bg-indigo-900 border border-indigo-700 text-slate-200 text-sm leading-relaxed chat-markdown"
            >
              <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
                {renderMath(m.content)}
              </ReactMarkdown>
            </div>
          )
        )}

        {loading && (
          <div className="self-start px-4 py-2 rounded-lg bg-indigo-900 border border-indigo-700 text-slate-500 text-sm">
            <span className="animate-pulse">...</span>
          </div>
        )}
      </div>

      {/* File preview chip */}
      {file && (
        <div className="flex items-center gap-2 px-3 py-1 rounded bg-indigo-900 border border-indigo-700 text-slate-300 text-xs shrink-0">
          <span>📎 {file.name}</span>
          <button
            type="button"
            onClick={() => { setFile(null); if (fileInputRef.current) fileInputRef.current.value = ""; }}
            className="text-slate-500 hover:text-red-400 transition-colors ml-auto"
          >
            ✕
          </button>
        </div>
      )}

      {/* Input bar */}
      <form onSubmit={handleSubmit} className="flex gap-2 shrink-0">

        {/* File upload button */}
        <button
          type="button"
          onClick={() => fileInputRef.current?.click()}
          disabled={loading}
          title="Upload image or PDF"
          className="px-3 py-2 rounded bg-indigo-900 border border-indigo-600 text-slate-400
                     hover:text-slate-200 hover:border-indigo-400 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          📎
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,.pdf"
          onChange={handleFileChange}
          className="hidden"
        />

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a problem or question..."
          disabled={loading}
          className="flex-1 px-4 py-2 rounded bg-violet-950 border border-indigo-600
                     text-slate-100 placeholder-slate-500
                     focus:outline-none focus:border-indigo-400
                     disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={loading || (!input.trim() && !file)}
          className="px-5 py-2 rounded bg-indigo-600 hover:bg-indigo-500
                     text-slate-100 font-semibold transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "..." : "Send"}
        </button>
      </form>
    </div>
  );
}
