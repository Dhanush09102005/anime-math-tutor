import { useEffect } from "react";

// Topic catalogue for v1.2.0. Every topic below now has a working generator
// in math_engine/generate.py's TOPIC_GENERATORS registry.
// `id` must match the topic string that registry expects — keep these two
// in sync when adding future topics.
const TOPIC_CATEGORIES = [
  {
    label: "Foundations",
    topics: [
      { id: "linear_equations", name: "Linear Equations", active: true },
      { id: "numbers", name: "Playing with Numbers", active: true },
      { id: "logarithms", name: "Logarithms", active: true },
    ],
  },
  {
    label: "Algebra",
    topics: [
      { id: "quadratic_equations", name: "Quadratic Equations", active: true },
      { id: "progressions", name: "Progressions", active: true },
      { id: "binomial_theorem", name: "Binomial Theorem", active: true },
      { id: "complex_numbers", name: "Complex Numbers", active: true },
    ],
  },
  {
    label: "Trigonometry",
    topics: [
      { id: "trigonometry", name: "Trig, T-Functions & ITF", active: true },
    ],
  },
  {
    label: "Linear Algebra",
    topics: [
      { id: "linear_algebra", name: "Eigenvalues", active: true },
      { id: "matrices_determinants", name: "Matrices & Determinants", active: true },
    ],
  },
  {
    label: "Geometry",
    topics: [
      { id: "coordinate_geometry", name: "Coordinate Geometry", active: true },
      { id: "vectors_3d", name: "Vectors & 3D Geometry", active: true },
    ],
  },
  {
    label: "Calculus",
    topics: [
      { id: "calculus", name: "Limits, Derivatives & Integrals", active: true },
    ],
  },
  {
    label: "Probability & Statistics",
    topics: [
      { id: "probability", name: "P&C and Probability", active: true },
      { id: "statistics", name: "Statistics", active: true },
    ],
  },
  {
    label: "Sets & Relations",
    topics: [
      { id: "sets_relations", name: "Sets & Relations", active: true },
    ],
  },
];

function topicName(topicId) {
  return TOPIC_CATEGORIES.flatMap((category) => category.topics)
    .find((topic) => topic.id === topicId)?.name ?? topicId.replaceAll("_", " ");
}

export default function TopicSelect({ onSelect, onBack, loading, preSelectedTopic = null }) {
  // When arriving from SyllabusPage "Practice →", skip the picker and
  // auto-select the topic immediately. A brief render still happens so the
  // user sees which topic was chosen before the session starts.
  useEffect(() => {
    if (preSelectedTopic) {
      onSelect(preSelectedTopic);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div className="flex flex-col items-center gap-10 w-full max-w-3xl">

      <div className="w-full flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-slate-500 hover:text-slate-300 text-xs tracking-wide transition-colors"
        >
          ‹ change mode
        </button>
      </div>

      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-wide text-slate-100">
          {preSelectedTopic ? "Starting syllabus practice" : "Choose your mission"}
        </h1>
        <p className="mt-2 text-slate-400 text-sm">
          {preSelectedTopic
            ? `${topicName(preSelectedTopic)} is selected and will start automatically.`
            : "Pick a topic. More get added every version."}
        </p>
      </div>

      <div className="w-full flex flex-col gap-6">
        {TOPIC_CATEGORIES.map((category) => (
          <div key={category.label} className="flex flex-col gap-2">
            <div className="text-slate-500 text-xs tracking-widest uppercase px-1">
              {category.label}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              {category.topics.map((t) => (
                <button
                  key={t.id}
                  onClick={() => t.active && onSelect(t.id)}
                  disabled={!t.active || loading}
                  className={`
                    relative rounded-xl border px-4 py-3 text-left
                    transition-all duration-200
                    ${t.active
                      ? t.id === preSelectedTopic
                        ? "border-yellow-500 bg-indigo-800 scale-[1.02] cursor-pointer"
                        : "border-indigo-600 bg-indigo-900 hover:border-indigo-400 hover:scale-[1.02] cursor-pointer"
                      : "border-indigo-900 bg-violet-950 opacity-40 cursor-not-allowed"
                    }
                  `}
                >
                  <div className="text-slate-100 text-sm font-semibold">{t.name}</div>

                  {loading && t.active && (
                    <div className="absolute inset-0 bg-violet-950/60 rounded-xl flex items-center justify-center">
                      <span className="text-slate-300 text-xs animate-pulse">Loading...</span>
                    </div>
                  )}

                  {!t.active && (
                    <div className="absolute top-2 right-2 px-2 py-0.5 rounded bg-indigo-700 text-slate-400 text-[10px]">
                      Soon
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
