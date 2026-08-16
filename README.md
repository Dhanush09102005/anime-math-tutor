# Anime Math Tutor

An adaptive math tutor where anime characters teach you — in character. Pick a sensei, pick how you want to learn — quick practice or an actual conversation — and get real-time LLM-generated teaching in their voice. Currently featuring **Kakashi Hatake**, across **16 math topics**.

---

## Demo

> Select Kakashi → pick a topic → either drill problems back-to-back, or just talk to him — ask questions, go on tangents, ask for a problem whenever you want one

Character art changes based on how you're doing. Nail a streak and he actually notices.

---

## Stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite + Tailwind CSS v4 |
| Backend | Python, FastAPI, SymPy |
| LLM | Llama 3.3 70B via HuggingFace → Groq |

---

## Project structure

```
Anime_school/
├── backend/
│   ├── main.py                   FastAPI app, CORS, router mounts
│   ├── schemas.py                Pydantic models, incl. AnswerShape enum, Chat models
│   ├── state.py                  Session cache + constants (now tracks mode: qna | chat)
│   ├── requirements.txt
│   ├── tutor.db                  SQLite database (gitignored)
│   ├── db/
│   │   └── database.py           Schema, init, session + attempt CRUD
│   ├── math_engine/
│   │   ├── generate.py           Problem generation — 16 topics, SymPy-backed
│   │   ├── verify.py             Shape-dispatched answer verification
│   │   ├── difficulty.py        Adaptive difficulty logic
│   │   └── chat_tools.py        NEW — wraps generate/verify as LLM tool-calls for chat mode
│   ├── personas/
│   │   ├── kakashi.json          Kakashi persona config
│   │   └── prompt_builder.py    Event classifier + LLM prompt assembler + chat system prompt
│   ├── llm_client/
│   │   └── hf_client.py         HuggingFace router → Llama 3.3 70B, with tool-calling + retry
│   └── routes/
│       ├── session.py            POST /session (now takes mode + topic)
│       ├── problem.py            POST /problem
│       ├── submit.py             POST /submit
│       └── chat.py              NEW — POST /chat, the agentic tool-calling loop
│
└── anime-tutor/
    └── src/
        ├── App.jsx               Phase machine: select → mode → topic → (problem/reaction | chat)
        ├── api/client.js         Fetch wrapper for all 4 endpoints
        ├── components/
        │   ├── CharacterSelect.jsx
        │   ├── ModeSelect.jsx       NEW — "Quick Practice" vs "Just Talk"
        │   ├── TopicSelect.jsx      Topic picker, grouped by category
        │   ├── CharacterPanel.jsx   Left-half mood image, shared by both modes
        │   ├── SessionHeader.jsx    Streak + mission rank
        │   ├── ProblemCard.jsx
        │   ├── ReactionPanel.jsx   Typewriter reaction display
        │   └── ChatWindow.jsx      NEW — scrolling chat interface
        └── assets/
            ├── kakashi/          Mood images (one per event type)
            └── characters/       Character select card images
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
HF_TOKEN=your_huggingface_token_here
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

> **Note on the HF token:** Hugging Face's free/PRO inference credits are a small **monthly** pool (PRO is $2/month across all providers), not a daily-reset rate limit — it's easy to exhaust mid-testing session. If a request starts returning a 402 ("depleted your monthly included credits"), that's this cap, not a bug. Calling Groq directly instead of through HF's router would trade this for a **daily**-reset rate limit, which is friendlier for dev testing, **and would likely also fix the tool-calling reliability issues chat mode currently patches around** (see "Problems faced" below) — discussed repeatedly, not yet implemented. `hf_client.py` still points at the HF router.

---

## How it works

Four API calls drive the app:

```
POST /session   { persona_id, mode, topic? }        → session_id
POST /problem   { session_id, topic? }               → problem text + difficulty + answer_shape
POST /submit    { session_id, problem_id, answer }   → correct/wrong + LLM reaction
POST /chat      { session_id, message }              → free-form reply + mood + streak + difficulty
```

The backend never sends the answer to the frontend. Verification is server-side only, via SymPy — **the LLM never grades answers**, it only reacts to an already-verified result. This holds in both modes: in Quick Practice, verification happens directly in `/submit`; in chat mode, the LLM can only find out if an answer is right by calling a `check_answer` tool that runs the same SymPy verification underneath — it cannot decide correctness on its own authority. This is a core, deliberate design principle, reaffirmed multiple times (including once when LLM-based grading was proposed and explicitly rejected on reliability grounds) rather than incidental.

### Two modes (v2.2)

- **Quick Practice** — the original flow. Problem, answer, instant reaction, repeat.
- **Just Talk** — free-form conversation. The student can ask for a problem, ask "why", go off-topic, ask for a different explanation — the LLM drives the whole turn, reaching for tools (`get_next_problem`, `check_answer`) only when it actually needs to generate or verify something, never to decide correctness itself.

Both modes share the same character, the same math engine, and the same mood-image system. Chat mode's mood signal is currently a coarse `correct_first_try` / `incorrect` / `default` mapping — not yet the full 10-category event taxonomy Quick Practice has.

### Topics (16 live)

| Category | Topics |
|---|---|
| Foundations | Linear Equations, Playing with Numbers, Logarithms |
| Algebra | Quadratic Equations, Progressions, Binomial Theorem, Complex Numbers |
| Trigonometry | Trig, T-Functions & ITF |
| Linear Algebra | Linear Algebra (eigenvalues), Matrices & Determinants |
| Geometry | Coordinate Geometry, Vectors & 3D Geometry |
| Calculus | Limits, Derivatives & Definite Integrals |
| Probability & Statistics | P&C and Probability, Statistics |
| Sets & Relations | Sets & Relations |

**Known limitation:** these problems are procedurally generated by SymPy and are **correctness-guaranteed, but not true JEE-Advanced difficulty** — e.g. Statistics is currently mean-only (not variance/SD), Vectors is dot-product-only (not triple products/coplanarity). A deliberate scoping choice — see "Answer shapes" below and the Roadmap for the planned fix (LLM-generated problems, SymPy-verified).

### Answer shapes

Every problem declares an `answer_shape` (in `schemas.py`), which determines both how `verify.py` checks it and what input widget the frontend renders:

| Shape | Meaning | Status |
|---|---|---|
| `single_value` | one number/fraction | ✅ implemented |
| `multi_value` | a set of valid answers (e.g. quadratic roots) | ✅ implemented |
| `vector_or_matrix` | ordered tuple/grid, not a scalar | ⛔ not implemented |
| `expression` | symbolic equivalence (e.g. equation of a circle) | ⛔ not implemented |

All 16 current topics are deliberately phrased to land on `single_value` or `multi_value` (e.g. "find the determinant" rather than "find the resulting matrix") specifically so they could go live without needing the other two shapes built first.

### Chat mode's tool-calling loop

`routes/chat.py` runs a loop: send the conversation + available tools to the LLM → if it wants to call `get_next_problem` or `check_answer`, execute it via `math_engine/chat_tools.py` (which wraps the exact same `generate_problem`/`verify_answer` functions Quick Practice uses) → feed the result back → repeat until the model returns a plain-text reply instead of a tool call. Capped at 4 iterations so a model that won't settle can't hang a request forever.

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
| `frustration_warning` | 2–3 consecutive wrong answers |
| `full_frustration` | 4+ consecutive wrong answers |
| `give_up_request` | User asked for a hint |
| `topic_mastered` | Correct at difficulty ≥ 8 (once per session) |
| `not_serious` | Non-numeric or unreduced-arithmetic input |

`mistake_type` (a separate, more granular signal feeding into the LLM prompt) includes `"partial"` for `multi_value` problems — e.g. getting one root of a quadratic right and the other wrong.

### Persona system

Each character is a JSON file in `backend/personas/`. The LLM is given the character's philosophy, tone, speech patterns, and (in Quick Practice) an example reaction line for the current event, or (in chat mode) the same persona fields reframed for sustained free-form conversation — then generates a fresh response. Nothing is hardcoded.

---

## Adding character mood images

Drop images into `src/assets/kakashi/`, then import them in `src/assets/kakashi/index.js`:

```
default.png           idle / between problems
correct_first_try.png
correct_streak.png
incorrect.png
repeated_mistake.png
give_up_request.png
topic_mastered.png
```

---

## Problems faced (for interview review)

Real bugs hit and fixed during development, in the order they came up. Each one includes what actually broke, why, and how it was found — not just the patch.

**1. Leading-zero input parsing (`-05` rejected)**
SymPy's expression parser treated zero-padded numeric literals like `"-05"` as octal notation and rejected them, even though a student typing that clearly meant `-5`. Fixed by stripping leading zeros (preserving sign and decimals) before handing the string to SymPy's parser, rather than trying to make the parser itself more lenient.

**2. Schema change broke a dependent route (`ValidationError` on `/problem`)**
Adding a new required field (`answer_shape`) to a Pydantic response model broke the route that constructed it, since that route was written before the field existed and nobody had gone back to update it. Predicted before it happened (the dependency was known), but still had to actually be triggered and fixed — a clean example of why adding a required field to a shared schema needs a check of every place that schema gets constructed, not just the schema definition itself.

**3. Correct answers wrongly flagged as "lazy input" (`not_serious` false positive)**
A heuristic meant to catch students typing unreduced arithmetic (e.g. `"11-2"` instead of `"9"`) only recognized plain digit strings as "the real answer." Once topics with genuinely fractional (probability, statistics) or π-based (trigonometry) correct answers existed, a **correct** answer like `"3/8"` or `"5*pi/6"` got flagged as compound/lazy input, and the character would accuse the student of joking around for a right answer. Root cause: the heuristic didn't know that "compound-looking" is only suspicious when the true answer *isn't* compound. Fixed by making the check depend on the actual canonical answer's form, not a topic-blind string pattern.

**4. Unbound variable on an untested code path (`UnboundLocalError` on give-up/hint)**
A variable was only ever assigned inside one branch of an `if/else`, and the other branch's logic several lines later assumed it always existed. The bug was invisible for a long time simply because that specific branch (the "give up" / hint request path) hadn't actually been clicked yet in testing — every other path exercised the code fine. Found the moment that specific button was tested live. A reminder that path coverage in manual testing matters as much as the code being "obviously correct" on read-through.

**5. A hand-applied fix lost its indentation**
A bugfix delivered as a code snippet (rather than a full file) got pasted into the editor with its indentation stripped, turning correctly-structured code inside an `if` block into flush-left code — a silent `IndentationError` waiting to happen. Led to a standing rule for the rest of the project: hand back whole, compiled-and-verified files for anything indentation-sensitive, rather than snippets meant to be manually merged in.

**6. Third-party API cost model surprise (HF monthly credit cap)**
Assumed a rate-limit-style "resets soon" quota; it was actually a small **monthly dollar-credit pool**, fully exhausted mid-testing session with no warning beforehand. Not a code bug, but a real lesson in reading a vendor's actual billing model rather than assuming it works like the free tiers you're used to — and in checking whether a comparable direct API (Groq, bypassing the extra middleman) has a fundamentally different, friendlier limit shape before building around the assumed one.

**7. Tool-calling responses leaking as literal text (`<function=name></function>` shown to the user)**
Chat mode's whole design depends on the LLM's "I want to call this tool" signal arriving in a structured field the code can check. Instead, some responses came back as a normal 200 with that signal rendered as **literal visible text** inside the reply — meaning the raw tag showed up in the chat UI instead of anything happening. Root cause, as best diagnosed: Hugging Face's router sits between this app and Groq's actual API, and isn't reliably translating Llama's native function-call output into the structured format the code expects. Fixed with a regex-based fallback: detect that exact text pattern, parse the intended function name/arguments out of it, strip it from the visible reply, and execute it exactly like a real tool call — a patch on top of an unreliable third-party layer, not a root fix.

**8. A second, different failure mode from the same root cause (malformed tool syntax → hard 400 error)**
Separately from #7, a slightly *malformed* version of that same function-call text (a single stray character) didn't come back as content at all — the router's own internal parser rejected the whole request outright with a `400 tool_use_failed` error before any reply was generated. Since there was no content in this case, the fallback text-parser from #7 had nothing to catch — this needed its own fix: catching that specific error code and retrying the request once, since the failures looked like one-off generation glitches rather than a consistent per-request failure.

**9. A bug in the fix for #8, caught by testing the fix itself**
The first version of that retry logic read the error's status code from the wrong level of nesting in the response body (`body["code"]` instead of the actual `body["error"]["code"]`), so the retry branch silently never triggered — the code looked reasonable on read-through, but a deliberately-reproduced test using the exact real error shape proved it wasn't working. Fixed once the actual nesting was confirmed directly against a real error object rather than assumed.

**10. Character defaulting to a math problem instead of responding to what was actually said**
Told the character "love you sensei, say you love me back," and instead of engaging with that at all, it responded with an unrelated log-base problem. Root cause: the tool description for "generate a new problem" included "call this when starting a session" as a trigger condition, which the model interpreted broadly enough to override the actual content of the message — combined with no explicit instruction in the system prompt to prioritize responding to what the student said. Fixed via prompt wording: removed the "starting a session" auto-trigger, and added an explicit rule that responding to the actual message always comes first. **Not yet re-verified live as of the last update to this document** — see "Still open" in the roadmap below.

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
| v1.0.1 | Hotfix: `-05` now correctly accepted as `-5` (leading-zero normalisation) |
| v1.1.0 | 10-category event taxonomy, full conversation history, all reaction_bank lines + mood images wired |
| v1.2.0 | Answer-shape architecture (`single_value`/`multi_value`/`vector_or_matrix`/`expression`) generalized across schema, generation, and verification. 15 new topics (16 total). Character→topic→problem frontend flow. Fixed `not_serious` false-positive and give-up-path crash. |
| v2.2 (WIP, not yet tagged) | **Chat mode** — free-form conversation alongside Quick Practice, via LLM tool-calling (`get_next_problem`, `check_answer`) wrapping the existing SymPy engine. New mode-select step, new `/chat` endpoint, new `ChatWindow.jsx`. Found and patched two distinct HF-router tool-calling reliability bugs (raw-text leakage, malformed-syntax hard failures) and a bug in the retry-fix itself. Fixed a prompt-wording issue causing the character to default to giving a problem instead of responding to off-topic messages — not yet re-verified live. |

---

## Roadmap

### v1.x — Improving Kakashi + expanding content — closed out as of v1.2.0
- [x] Improved Kakashi LLM response quality
- [x] More math topics — 16 landed
- [x] Topic/subtopic selection
- [ ] Sukuna, Makima, Mahito added to same depth as Kakashi — moved to v3
- [ ] Per-character theming and frontend improvements — moved to v3
- [ ] (small, still open) `not_serious` UI bug in Quick Practice's `ReactionPanel`

### v2.x — Multi-user platform
- [ ] Authentication, user accounts
- [ ] Per-user progress, analytics, history
- [ ] Full database, multiple pages, proper routing
- [x] **v2.2 — Chat mode** (see version history) — landed as a sub-milestone ahead of auth/accounts, since it didn't depend on them
  - [ ] Full 10-category mood/event parity for chat mode (currently a coarse 3-state mapping)
  - [ ] Re-verify the off-topic-message prompt fix live — still open as of the last update
  - [ ] Migrate off HF's router to Groq directly — now motivated by *two* separate problems (credit caps AND tool-calling reliability), not just one

### v3.x — Immersive experience *(long-term)*
- [ ] Animated characters, voice acting trained on source material
- [ ] Dialogue-box UI, doubt-solving chat, session summaries
- [ ] Real JEE Mains + Advanced question bank
- [ ] **Replace procedural generation with LLM-generated problems, SymPy-verified.** The LLM generates a problem in a structured, parseable form; SymPy independently solves it and checks the LLM's claimed answer before the problem ever reaches a student — mismatches are silently discarded and regenerated. SymPy remains the sole source of correctness — the LLM still never grades or asserts an answer is right.
- [ ] `vector_or_matrix` and `expression` answer-shape verification (equation of a line/circle/conic, matrix results, indefinite integrals, differential equations)

---

## Environment variables

| Variable | Where | Description |
|---|---|---|
| `HF_TOKEN` | `backend/.env` | HuggingFace API token for LLM access |
