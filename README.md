# Anime Math Tutor

An adaptive math tutor where anime characters teach you — in character. Pick a sensei, pick how you want to learn — quick practice or an actual conversation — and get real-time LLM-generated teaching in their voice. Currently featuring **Kakashi Hatake, Sukuna, Makima, and Goku**, across **16 math topics**.

---

## Demo

> Select a character → pick a topic → either drill problems back-to-back, or just talk to them — ask questions, go on tangents, ask for a problem whenever you want one

Character art changes based on how you're doing. Nail a streak and they actually notice — in their own voice, not a generic one.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS v4 |
| Backend | Python, FastAPI, SymPy |
| LLM | `openai/gpt-oss-120b` via Groq, direct (no longer routed through HuggingFace) |

---

## Project structure

```
Anime_school/
├── backend/
│   ├── main.py                   FastAPI app, CORS, router mounts
│   ├── schemas.py                Pydantic models, incl. AnswerShape enum, Chat models
│   ├── state.py                  Session cache + constants (tracks mode: qna | chat)
│   ├── requirements.txt
│   ├── tutor.db                  SQLite database (gitignored)
│   ├── .env                      GROQ_API_KEY (gitignored) — HF_TOKEN no longer used
│   ├── db/
│   │   └── database.py           Schema, init, session + attempt CRUD
│   ├── math_engine/
│   │   ├── generate.py           Problem generation — 16 topics, SymPy-backed
│   │   ├── verify.py             Shape-dispatched answer verification
│   │   ├── difficulty.py        Adaptive difficulty logic
│   │   └── chat_tools.py        Wraps generate/verify as LLM tool-calls for chat mode.
│   │                              `answer` param accepts string OR number (see
│   │                              "Problems faced" — Groq validates tool-call args
│   │                              server-side against this schema).
│   ├── personas/
│   │   ├── kakashi.json          Kakashi persona config, incl. fallback_line
│   │   ├── sukuna.json           Sukuna persona config, incl. fallback_line
│   │   ├── makima.json           Makima persona config, incl. fallback_line
│   │   ├── goku.json             Goku persona config, incl. fallback_line
│   │   └── prompt_builder.py    Event classifier + LLM prompt assembler + chat system prompt
│   ├── llm_client/
│   │   └── hf_client.py         MIGRATED — now calls Groq's API directly (OpenAI-
│   │                              compatible endpoint), not HF's router. File name
│   │                              kept as-is to avoid touching every import site;
│   │                              content is fully Groq-direct. Sets
│   │                              reasoning_format="hidden" — required for Groq's
│   │                              reasoning-capable models (see "Problems faced").
│   └── routes/
│       ├── session.py            POST /session (takes mode + topic)
│       ├── problem.py            POST /problem
│       ├── submit.py             POST /submit
│       └── chat.py              POST /chat — the agentic tool-calling loop. Now
│                                  falls back on empty string replies (not just
│                                  None), forces one final tools-omitted call if the
│                                  loop exhausts without a reply, and uses each
│                                  persona's own fallback_line instead of a
│                                  hardcoded Kakashi-flavored one.
│
└── anime-tutor/
    └── src/
        ├── App.jsx               Phase machine: select → mode → topic → (problem/reaction | chat)
        ├── api/client.js         Fetch wrapper for all 4 endpoints
        ├── components/
        │   ├── CharacterSelect.jsx   CHARACTERS array now exported — reused by
        │   │                          SessionHeader.jsx for name/title lookup
        │   ├── ModeSelect.jsx       "Quick Practice" vs "Just Talk"
        │   ├── TopicSelect.jsx      Topic picker, grouped by category. "Linear
        │   │                          Algebra" topic renamed to "Eigenvalues" —
        │   │                          was colliding visually with its own category
        │   │                          header of the same name
        │   ├── CharacterPanel.jsx   Left-half mood image. NOW supports multiple
        │   │                          personas via a personaId prop + a
        │   │                          MOOD_REGISTRIES lookup, instead of being
        │   │                          hardcoded to kakashiMoods only
        │   ├── SessionHeader.jsx    Streak + difficulty. NOW reads the actual
        │   │                          active persona's name/title (was hardcoded
        │   │                          to "Kakashi Hatake" regardless of who was
        │   │                          selected). Naruto-specific D/C/B/A/S rank
        │   │                          system replaced with a universal
        │   │                          Novice→Master difficulty label
        │   ├── ProblemCard.jsx
        │   ├── ReactionPanel.jsx   Typewriter reaction display
        │   └── ChatWindow.jsx      Scrolling chat interface
        └── assets/
            ├── kakashi/           Mood images (one per event type)
            ├── sukuna/            Mood images — full set, wired
            ├── makima/            Mood images — pending as of this document
            ├── goku/              Mood images — pending as of this document
            └── characters/        Character select card images
```

---

## Running locally

**1. Backend**

```bash
cd backend
pip install -r requirements.txt
```

Create a `.env` file in `backend/`:
```
GROQ_API_KEY=your_groq_key_here
```

```bash
uvicorn main:app --reload
# → http://localhost:8000
```

**2. Frontend**

```bash
cd anime-tutor
npm install
npm run dev
# → http://localhost:5173
```

> **Note on the Groq API key:** as of this version, LLM calls go straight to Groq's API (`https://api.groq.com/openai/v1`) instead of through Hugging Face's router. Grab a free key at [console.groq.com](https://console.groq.com) — no credit card required. Groq's free tier is a **daily-resetting rate limit** (~30 requests/min, ~1,000 requests/day, ~100K tokens/day for the models this project uses), not a monthly dollar-credit pool — it will not strand a demo mid-session the way HF's old monthly cap did, but it is a real limit, not unlimited.

---

## How it works

Four API calls drive the app:

```
POST /session   { persona_id, mode, topic? }        → session_id
POST /problem   { session_id, topic? }               → problem text + difficulty + answer_shape
POST /submit    { session_id, problem_id, answer }   → correct/wrong + LLM reaction
POST /chat      { session_id, message }              → free-form reply + mood + streak + difficulty
```

The backend never sends the answer to the frontend. Verification is server-side only, via SymPy — **the LLM never grades answers**, it only reacts to an already-verified result. This holds in both modes: in Quick Practice, verification happens directly in `/submit`; in chat mode, the LLM can only find out if an answer is right by calling a `check_answer` tool that runs the same SymPy verification underneath — it cannot decide correctness on its own authority. This is a core, deliberate design principle, reaffirmed multiple times (including once when LLM-based grading was proposed and explicitly rejected on reliability grounds) rather than incidental. **The LLM does not propose or generate problem content** — problems come entirely from `math_engine/generate.py`'s hand-written generators; the LLM only calls `get_next_problem` to request one and delivers it in character.

### Two modes

- **Quick Practice** — the original flow. Problem, answer, instant reaction, repeat.
- **Just Talk** — free-form conversation. The student can ask for a problem, ask "why", go off-topic, ask for a different explanation — the LLM drives the whole turn, reaching for tools (`get_next_problem`, `check_answer`) only when it actually needs to generate or verify something, never to decide correctness itself.

Both modes share the same character, the same math engine, and the same mood-image system. Chat mode's mood signal is currently a coarse `correct_first_try` / `incorrect` / `default` mapping — not yet the full 10-category event taxonomy Quick Practice has.

### Topics (16 live)

| Category | Topics |
|---|---|
| Foundations | Linear Equations, Playing with Numbers, Logarithms |
| Algebra | Quadratic Equations, Progressions, Binomial Theorem, Complex Numbers |
| Trigonometry | Trig, T-Functions & ITF |
| Linear Algebra | Eigenvalues, Matrices & Determinants |
| Geometry | Coordinate Geometry, Vectors & 3D Geometry |
| Calculus | Limits, Derivatives & Definite Integrals |
| Probability & Statistics | P&C and Probability, Statistics |
| Sets & Relations | Sets & Relations |

**Known, acknowledged limitation:** these problems are procedurally generated by SymPy and are **correctness-guaranteed, but not true JEE-Advanced difficulty or variety** — e.g. Statistics is currently mean-only (not variance/SD), Vectors is dot-product-only (not triple products, skew-line distances, foot-of-perpendicular problems, etc.), Logarithms and "Playing with Numbers" problems tend to land on a narrow, predictable range of small-integer answers. This was raised directly as a real concern this session (not just a known gap) — see "Open questions" below for the actual discussion and where it landed.

### Answer shapes

Every problem declares an `answer_shape` (in `schemas.py`), which determines both how `verify.py` checks it and what input widget the frontend renders:

| Shape | Meaning | Status |
|---|---|---|
| `single_value` | one number/fraction | ✅ implemented |
| `multi_value` | a set of valid answers (e.g. quadratic roots) | ✅ implemented |
| `vector_or_matrix` | ordered tuple/grid, not a scalar | ⛔ not implemented |
| `expression` | symbolic equivalence (e.g. equation of a circle) | ⛔ not implemented |

All 16 current topics are deliberately phrased to land on `single_value` or `multi_value` specifically so they could go live without needing the other two shapes built first.

### Chat mode's tool-calling loop

`routes/chat.py` runs a loop: send the conversation + available tools to the LLM → if it wants to call `get_next_problem` or `check_answer`, execute it via `math_engine/chat_tools.py` (which wraps the exact same `generate_problem`/`verify_answer` functions Quick Practice uses) → feed the result back → repeat until the model returns a plain-text reply instead of a tool call. Capped at 4 iterations so a model that won't settle can't hang a request forever. **If the loop exhausts all 4 iterations without ever producing a plain-text reply** (the model kept calling tools every turn), one final call is made with `tools` withheld entirely — this forces a plain-text response instead of another tool call, since there's nothing left to call. If even that comes back empty, the active persona's own `fallback_line` is used, so a failed turn still sounds like the character instead of a generic error or a blank message.

### Adaptive difficulty

Problems scale from difficulty 1–10 based on streak:
- streak ≥ 5 correct → +2 difficulty
- streak ≥ 3 correct → +1 difficulty
- wrong → −1 difficulty

### Event system (Quick Practice)

Every submit maps to one of 10 event categories:

| Event | Condition |
|---|---|
| `correct_first_try` | Correct, streak < 3, no milestone |
| `correct_streak` | Correct, streak ≥ 3 |
| `difficulty_milestone` | Correct answer pushed difficulty to 3, 5, 7, or 9 |
| `comeback` | First correct answer after a string of wrong answers |
| `incorrect` | Wrong answer, first time this mistake type |
| `repeated_mistake` | Wrong answer, same mistake type as last time |
| `frustration_warning` | 5–6 consecutive wrong answers |
| `full_frustration` | 7+ consecutive wrong answers |
| `give_up_request` | User asked for a hint |
| `topic_mastered` | Correct at difficulty ≥ 8 (once per session) |
| `not_serious` | Non-numeric or unreduced-arithmetic input |

`mistake_type` (a separate, more granular signal feeding into the LLM prompt) includes `"partial"` for `multi_value` problems — e.g. getting one root of a quadratic right and the other wrong.

**Frustration thresholds were retuned this session** (previously 2–3 / 4+) — a wider band was requested so `repeated_mistake` has more room to fire before frustration events kick in.

### Persona system

Each character is a JSON file in `backend/personas/`. The LLM is given the character's philosophy, tone, speech patterns, and (in Quick Practice) an example reaction line for the current event, or (in chat mode) the same persona fields reframed for sustained free-form conversation — then generates a fresh response. Nothing is hardcoded. Each persona now also defines a `fallback_line` — an in-character line used if the LLM produces no usable reply for a turn, instead of a hardcoded generic message.

**Four personas now exist:** Kakashi Hatake (Copy Ninja — laid-back, dry, quietly perceptive), Sukuna (King of Curses — contemptuous, threatening, barely satisfied even when impressed), Makima (Control Devil — calm, calculating, unsettling), Goku (loud, earnest, frames everything as training/sparring). Hisoka and Mahito were considered and deliberately dropped from the roster (see CONTEXT.md for reasoning).

---

## Adding character mood images

Drop images into `src/assets/<persona_id>/`, then import them in `src/assets/<persona_id>/index.js`, exporting a `<personaId>Moods` object:

```
default.png           idle / between problems
correct_first_try.png
correct_streak.png
incorrect.png
repeated_mistake.png
give_up_request.png
frustration_warning.png
full_frustration.png
topic_mastered.png
comeback.png
difficulty_milestone.png
```

Then wire it into `CharacterPanel.jsx`'s `MOOD_REGISTRIES` map (import the moods object, add one line to the registry), and flip that persona's `active: true` in `CharacterSelect.jsx`'s `CHARACTERS` array.

---

## Problems faced (for interview review)

Real bugs hit and fixed during development, in the order they came up. Each one includes what actually broke, why, and how it was found — not just the patch.

**1. Leading-zero input parsing (`-05` rejected)**
SymPy's expression parser treated zero-padded numeric literals like `"-05"` as octal notation and rejected them, even though a student typing that clearly meant `-5`. Fixed by stripping leading zeros (preserving sign and decimals) before handing the string to SymPy's parser, rather than trying to make the parser itself more lenient.

**2. Schema change broke a dependent route (`ValidationError` on `/problem`)**
Adding a new required field (`answer_shape`) to a Pydantic response model broke the route that constructed it, since that route was written before the field existed. A clean example of why adding a required field to a shared schema needs a check of every place that schema gets constructed, not just the schema definition itself.

**3. Correct answers wrongly flagged as "lazy input" (`not_serious` false positive)**
A heuristic meant to catch students typing unreduced arithmetic (e.g. `"11-2"` instead of `"9"`) only recognized plain digit strings as "the real answer." Once topics with genuinely fractional or π-based correct answers existed, a **correct** answer like `"3/8"` or `"5*pi/6"` got flagged as compound/lazy input. Fixed by making the check depend on the actual canonical answer's form, not a topic-blind string pattern.

**4. Unbound variable on an untested code path (`UnboundLocalError` on give-up/hint)**
A variable was only ever assigned inside one branch of an `if/else`; the other branch assumed it always existed. Invisible until that specific path (give-up/hint) was actually clicked live. A reminder that path coverage in manual testing matters as much as code looking correct on read-through.

**5. A hand-applied fix lost its indentation**
A bugfix delivered as a snippet got pasted with its indentation stripped, turning correctly-structured code inside an `if` block into flush-left code. Led to a standing rule: hand back whole, compiled files for anything indentation-sensitive, not snippets meant to be manually merged in.

**6. Third-party API cost model surprise (HF monthly credit cap)**
Assumed a rate-limit-style "resets soon" quota; it was actually a small **monthly dollar-credit pool**, fully exhausted mid-testing with no warning. A real lesson in reading a vendor's actual billing model rather than assuming it works like a familiar free tier.

**7. Tool-calling responses leaking as literal text (`<function=name></function>` shown to the user)**
Some responses from HF's router came back as a normal 200 with the model's intended tool call rendered as literal visible text instead of a structured field. Root cause: HF's router sat between this app and the actual model provider and wasn't reliably translating function-call output into the structured format expected. Patched with a regex-based fallback parser — later made moot by migrating off the router entirely (see #11).

**8. A second, different failure mode from the same root cause (malformed tool syntax → hard 400 error)**
A slightly malformed version of that same function-call text caused the router's own parser to reject the whole request outright with a `400 tool_use_failed` error, with no content to fall back on. Fixed with a catch-and-retry-once wrapper.

**9. A bug in the fix for #8, caught by testing the fix itself**
The first version of that retry logic read the error's status code from the wrong level of nesting in the response body, so the retry branch silently never triggered. Fixed once the actual nesting was confirmed against a real error object.

**10. Character defaulting to a math problem instead of responding to what was actually said**
Told the character something personal/off-topic, and it responded with an unrelated math problem instead of engaging. Root cause: the tool description for "generate a new problem" included an over-broad trigger condition, combined with no explicit instruction to prioritize responding to the actual message. Fixed via prompt wording. Verified live: the character now responds in-character to off-topic messages without firing a tool call — though it can still soften into a mild redirect toward math rather than staying fully off-topic. Accepted as good enough as-is.

**11. Groq deprecated the model this app was built on, breaking every LLM call (`404 model_not_found`)**
Mid-project, Groq deprecated `llama-3.3-70b-versatile` — the exact model this project used, confirmed via Groq's own announcement (June 17, 2026), with `openai/gpt-oss-120b` and `qwen/qwen3.6-27b` recommended as replacements. This landed on top of an already-planned migration from HF's router to calling Groq directly (motivated by the monthly credit cap in #6, and suspected — correctly — to also be the real fix for #7/#8's tool-calling reliability issues). Fixed by migrating `hf_client.py` to Groq's direct OpenAI-compatible endpoint and swapping to a currently-supported model.

**12. Reasoning-model output leaking `<think>...</think>` blocks directly into chat replies**
After switching to `qwen/qwen3.6-27b` (a reasoning-capable model), replies started arriving as raw, malformed-looking internal monologue instead of clean in-character text — and were also getting cut off mid-thought, since the reasoning was consuming the response's token budget before the model ever reached its actual answer. Root cause: reasoning models on Groq emit their internal reasoning directly into `.content` by default; Groq's API requires an explicit `reasoning_format` parameter (`"hidden"` or `"parsed"`) to suppress this, especially when tool calls are involved. Fixed by setting `reasoning_format="hidden"` on every completion call and raising `max_tokens` to give the model headroom.

**13. Groq's tool-schema validation rejected numeric answers sent as JSON numbers instead of strings**
The `check_answer` tool's schema declared `answer` as type `"string"` only. Once tool-calling worked reliably (post #11/#12), a new failure appeared: Groq validates tool-call arguments server-side against the declared schema before the request ever reaches this app's code, and the model was sending bare numeric answers (e.g. `4`) as a raw JSON number, not a string — triggering a hard `400 tool_use_failed`, schema-mismatch error. Fixed by widening the schema to accept `["string", "number"]`.

**14. Empty-string LLM replies silently rendered as blank chat bubbles**
The fallback-reply check only tested for `None` (`if final_reply is None`). Some models return an empty string `""` instead of `None` when they produce nothing usable for a turn — which is falsy but not `None`, so it slipped past the check and got stored/displayed as a blank message bubble instead of triggering the fallback. Fixed by checking `if not final_reply` instead, which catches `None`, `""`, and whitespace-only strings alike.

**15. Character name and rank system hardcoded to Kakashi regardless of active persona**
`SessionHeader.jsx` displayed the literal string "Kakashi Hatake" and a Naruto-specific D/C/B/A/S "mission rank" system no matter which character was actually selected — meaning Sukuna's chat window showed his dialogue under a "Kakashi Hatake" header. Neither bug had been caught because `personaId` was never passed down from `App.jsx` in the first place; the component had no way to know who was active. Fixed by exporting the existing character-name lookup table from `CharacterSelect.jsx`, importing it into `SessionHeader.jsx`, and threading a new `personaId` prop through from `App.jsx`. The rank system was also replaced with a universal Novice→Master difficulty label, since letter ranks tied to a specific show made no sense once other characters existed.

**16. Topic name visually duplicating its own category header**
The "Linear Algebra" topic sat directly under a "LINEAR ALGEBRA" category header, reading as an accidental duplicate rather than two different things. The topic itself is really about eigenvalue problems specifically. Fixed by renaming the display label to "Eigenvalues" (the underlying `id` used by the backend's generator registry was left untouched, since renaming that would require a matching backend change for no benefit).

---

## Version history

| Version | What landed |
|---|---|
| v0.1.0 | math_engine core (generate / verify / difficulty) + React + Vite frontend scaffold |
| v0.1.1 | Kakashi persona JSON + prompt_builder complete, pipeline tested in isolation |
| v0.2.0 | Full LLM integration — end-to-end pipeline proven live via REPL |
| v0.3.0 | FastAPI layer: `/session`, `/problem`, `/submit` wired over HTTP; router pattern; tested via Swagger |
| v0.4.0 | React frontend: all components, mood-image system tied to event categories, api/client.js |
| v1.0.0 | SQLite persistence, `not_serious` event, verify.py fixes, README — completes the vertical slice |
| v1.0.1 | Hotfix: `-05` correctly accepted as `-5` (leading-zero normalisation) |
| v1.1.0 | Conversation history, 10-category event taxonomy, frustration arc, mistake-specific feedback, difficulty milestones, all mood images wired |
| v1.2.0 | Answer-shape architecture (`single_value` / `multi_value`) generalised across schema, generation, and verification. 15 new topics (16 total). Topic selection frontend flow. Fixed `not_serious` false-positive on fractional/π answers and give-up path crash. |
| v1.3.0 | Chat mode — free-form conversation via LLM tool-calling (`get_next_problem`, `check_answer`) wrapping the existing SymPy engine. New `/chat` endpoint, `ChatWindow.jsx`, mode-select step. Patched two HF-router tool-calling bugs and a retry-logic bug. |
| v1.4.0 | Three new personas — Sukuna, Makima, Goku (Hisoka/Mahito considered and dropped) — persona JSONs, Sukuna's mood images + wiring fully done, Makima/Goku JSONs done but images/testing pending. Migrated off HF's router to Groq direct (`hf_client.py`), forced by both the monthly-credit cap and a mid-project Groq model deprecation. Fixed reasoning-model `<think>`-leak, tool-schema type mismatch, empty-string fallback bug, hardcoded-Kakashi header bug, and the Linear Algebra/Eigenvalues naming collision. Frustration thresholds retuned (5+/7+, was 2+/4+). Off-topic-message prompt fix (v1.3.0's #10) verified live. |
| v2.0.0 | Chat mode revamped into teaching mode. Accepts text, image, or PDF. New `extractor.py` (vision model for images, pdfplumber for typed PDFs, PyMuPDF fallback for scanned). New `solver.py` (SymPy-backed teaching solver for equations, derivatives, integrals). `/chat` now accepts multipart form data. `ChatWindow.jsx` gains file upload. No difficulty tracking or mood changes in chat mode. `ChatResponse` simplified (streak/difficulty removed). |

---

## Roadmap

### v1.x — Kakashi + content expansion + persona roster ✅ closed out at v1.4.0
- [x] Improved Kakashi LLM response quality — conversation history, 10-event taxonomy, frustration arc
- [x] More math topics — 16 live
- [x] Topic selection frontend flow
- [x] Chat mode — free-form conversation alongside Quick Practice
- [x] Sukuna, Makima, Goku — persona JSONs written (Hisoka/Mahito dropped from the plan)
- [x] Sukuna — fully wired (images, frontend activation)
- [ ] Makima, Goku — mood images, live testing, frontend activation still pending

### v2.x — Multi-user platform
- [x] v2.0.0 — Chat mode revamped into teaching mode (text/image/PDF input, SymPy-solved, character-explained)
- [ ] Makima, Goku — mood images, live testing, frontend activation
- [ ] Authentication, user accounts
- [ ] Per-user progress, analytics, history dashboards
- [ ] Full database schema for users, multiple pages, proper routing
- [ ] `not_serious` UI bug in Quick Practice
- [ ] Hint that actually teaches
- [ ] Full 10-category mood/event parity for chat mode

### v3.x — Immersive experience *(long-term)*
- [ ] Animated characters, voice acting trained on source material
- [ ] Dialogue-box UI, doubt-solving chat, session summaries, periodic tests
- [ ] Real JEE Mains + Advanced question bank
- [ ] `vector_or_matrix` and `expression` answer-shape verification

---

## Open questions (unresolved as of this document — read before making assumptions)

**Problem generation depth/variety.** Raised directly this session as a real, specific concern — not a vague "make it better" ask. Current generators produce narrow, predictable problems (e.g. logarithm answers mostly land in the 1–4 range, "numbers" topic is remainder-only). A hybrid approach was discussed at length — LLM proposes a problem's setup/structure, SymPy independently solves it from the symbolic parameters to get the canonical answer (never trusting the LLM's stated answer), regenerating on degenerate cases — which does NOT violate the "no LLM grading" rule, since the LLM would never be judging correctness, only proposing structure. **This was discussed as feasible but was NOT decided as the direction to take** — the conversation moved into whether it's worth the scope at all versus focusing on other things, and that question was **left open, not resolved either way**. Do not assume this is scoped for v1.5, v2.x, or anywhere else without asking the user directly first.

**Public deployment.** The project's original hard constraint (personal/local use only, due to copyrighted characters) is being dropped at the user's explicit direction — they intend to actually deploy this for interview value. This is a genuine scope change from earlier context, not a misunderstanding. The copyright-risk conversation that justified the original constraint was about *personal* use; a public-facing deployment with the same copyrighted characters is a meaningfully different risk profile and deserves its own real discussion when deployment work actually starts — don't treat the old constraint's reasoning as automatically resolved just because the constraint itself was lifted.

**Docker/deployment infrastructure.** Discussed and explicitly deferred — not needed for the current single-user local dev setup, and the natural trigger point (if the DB moves off SQLite to something like Postgres for real multi-user support) hasn't happened yet. Revisit when v2.x's actual database work begins, not before.

---

## Environment variables

| Variable | Where | Description |
|---|---|---|
| `GROQ_API_KEY` | `backend/.env` | Groq API key for direct LLM access (replaces the old `HF_TOKEN`) |
