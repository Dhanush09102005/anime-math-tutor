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
| Frontend | React 19 + Vite + Tailwind CSS v4 + React Router 7 |
| Backend | Python, FastAPI, SymPy |
| Database | PostgreSQL, SQLAlchemy, Alembic migrations |
| Auth | JWT (httpOnly cookie) + Google OAuth (Authlib) |
| LLM | `openai/gpt-oss-120b` via Groq, direct (no longer routed through HuggingFace) |
| Deployment | Docker Compose (`db` + `backend` + `frontend` services) |

---

## Project structure

```
Anime_school/
├── backend/
│   ├── main.py                   FastAPI app, CORS, router mounts
│   ├── schemas.py                Pydantic models, incl. AnswerShape enum, Chat models
│   ├── state.py                  Session cache + constants (tracks mode: qna | chat)
│   ├── requirements.txt
│   ├── db/
│   │   ├── database.py           PostgreSQL engine and SQLAlchemy session dependency
│   │   ├── models.py             Users, sessions, and attempts
│   │   └── crud.py               Persistence and analytics
│   ├── math_engine/
│   │   ├── generate.py           Procedural + validated hybrid generators for 16 topics
│   │   ├── verify.py             SymPy verification for four answer shapes
│   │   ├── difficulty.py        Adaptive difficulty logic
│   │   └── chat_tools.py        Legacy tool-calling helpers (not used by current chat route)
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
│       ├── submit.py             POST /submit and /hint
│       ├── chat.py               POST /chat — SymPy-backed teaching mode
│       └── analytics.py          Dashboard and syllabus progress
│
└── anime-tutor/
    └── src/
        ├── App.jsx               Phase machine: select → mode → topic → (problem/reaction | chat)
        ├── api/client.js         Authenticated API client, including hints/history
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
            ├── makima/            Mood images — wired
            ├── goku/              Mood images — wired
            └── characters/        Character select card images
```

---

## Running locally

The supported, simplest way to run the complete app is Docker Compose. SQLite is not supported; PostgreSQL is required.

### Prerequisites

- Windows, macOS, or Linux with Docker Desktop (or Docker Engine) and the Compose v2 plugin. On Windows, start Docker Desktop before running the commands below.
- Ports **80**, **8000**, and **5432** available on your machine.
- Internet access to download container images and call Google OAuth and Groq. Python 3 is optional; it is only used by the example command that generates random secrets.
- A Groq API key for chat, problem generation, hints, and reactions. Create one at [console.groq.com](https://console.groq.com).
- A Google OAuth web client for Google sign-in. Set its authorized redirect URI to exactly `http://localhost:8000/auth/oauth/google/callback`. Email/password login also exists, but the backend requires OAuth environment variables to be present at startup.
- Git, if cloning the project, and a terminal at the repository root (the directory containing `docker-compose.yml`).

### First run

1. Get the source and enter the repository directory:

   ```powershell
   git clone https://github.com/Dhanush09102005/anime-math-tutor.git
   Set-Location anime-math-tutor
   ```

   If you already have the source, just open a terminal in its repository root.

2. Create the root environment file. In PowerShell:

   ```powershell
   Copy-Item .env.example .env
   ```

   Edit `.env` and set:

   - `POSTGRES_PASSWORD` to a new strong database password.
   - `JWT_SECRET_KEY` and `SESSION_SECRET_KEY` to two different random secrets. Generate each with `python -c "import secrets; print(secrets.token_hex(32))"` and paste the outputs; do not use the example text.
   - `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` from your Google OAuth web client.
   - `GOOGLE_REDIRECT_URI` to `http://localhost:8000/auth/oauth/google/callback`, matching the URI registered with Google.
   - `GROQ_API_KEY` to your Groq API key.
   - Keep `FRONTEND_URL=http://localhost` and `VITE_API_URL=http://localhost:8000` for the Docker Compose local setup.

   `DATABASE_URL` in the example is for running the backend directly on your host. Compose supplies its own database URL to the backend container, so you do not need to edit this value when using the full Compose setup. Never commit `.env` or share its secrets.

3. Validate the Compose configuration, then build and start the app:

   ```powershell
   docker compose config --quiet
   docker compose up --build -d
   ```

   On the first run this downloads/builds the images, waits for PostgreSQL health, applies Alembic migrations automatically (including `0004` for resumable session state), and starts the API and nginx frontend. The `pgdata` and `avatars_data` named volumes preserve database data and uploaded avatars between container rebuilds.

4. Confirm the services started and the API is healthy:

   ```powershell
   docker compose ps
   Invoke-RestMethod http://localhost:8000/health
   ```

5. Open the app at **http://localhost**. The API is at **http://localhost:8000** and its interactive docs are at **http://localhost:8000/docs**. Register with email/password or use Google sign-in after configuring the OAuth client.

Active sessions are stored in PostgreSQL: chat turns, the current problem and its server-only answer, progress, and consecutive-wrong count survive API restarts. The active session ID is kept in the browser tab's session storage, and the app restores that session after refreshing the same tab. The resume endpoint returns the active problem prompt without its canonical answer. Closing the tab or starting a different session does not provide a session picker for resuming an older session.

### Stop, restart, and troubleshoot

```powershell
docker compose logs -f backend    # inspect API/provider/database startup errors
docker compose logs -f frontend   # inspect frontend container logs
docker compose down               # stop services; preserves database and avatars
docker compose up -d              # start again without rebuilding
docker compose up --build -d      # rebuild after changing source or configuration
```

PostgreSQL applies `POSTGRES_PASSWORD` only when its data volume is first initialized. Changing `.env` later does not change the existing database user's password. Prefer updating the database role to match; `docker compose down -v` deletes **all** Compose volumes, including database and avatar data, and should only be used if you intentionally want a full data reset.

### Frontend hot reload (optional)

To edit the frontend with Vite while using the containerized API and database, start only the backend dependencies:

```powershell
docker compose up --build -d db backend
Set-Location anime-tutor
npm ci
npm run dev
```

Open **http://localhost:5173**. The frontend API client calls `http://localhost:8000` directly; Vite does not proxy API requests. CORS is configured to allow the local Vite origin. Stop the Vite process with Ctrl+C and stop the containers from the repository root with `docker compose down`.

> **Groq usage:** model requests are sent directly to Groq's OpenAI-compatible API. Provider availability and rate limits apply; this project has not been verified against live model output as part of its automated tests.

### Deployment status

This repository is **not deployed**, and there is no public app URL to share. `http://localhost` is a local address that works only on the machine running Docker. A production launch still requires choosing a host/domain, HTTPS and reverse-proxy setup, production database and secrets, production OAuth origins/redirect URI, authorized public-use content/assets, and end-to-end smoke tests. Do not expose PostgreSQL to the public internet; the Compose API and database ports bind to loopback by default. Compose is a local run configuration, not a completed production deployment.

---

## How it works

The API surface includes:

```
POST /session   { persona_id, mode, topic? }        → session_id
POST /problem   { session_id, topic? }               → problem text + difficulty + answer_shape
POST /submit    { session_id, problem_id, answer }   → correct/wrong + LLM reaction
POST /hint      { session_id, problem_id }           → non-forfeiting hint
POST /chat      { session_id, message, file? }       → teaching reply
GET  /sessions/{session_id}/resume                  → restore owned active session
```

Quick Practice answer verification and teaching-mode equation solving use SymPy. The LLM never grades an answer. For all 16 topics, the LLM proposes bounded, topic-specific problem parameters; the backend validates them and constructs the prompt and canonical answer independently. SymPy is used where symbolic math is needed. The canonical answer remains server-side. Tests exercise two distinct proposal fixtures per topic, but actual model-generated variety and educational quality still need live-provider evaluation.

### Two modes

- **Quick Practice** — the original flow. Problem, answer, instant reaction, repeat.
- **Just Talk** — submit a question or math problem as text, image, or PDF. SymPy solves supported problem forms; the character explains the result or gives a clearly unverified general method when parsing is unsupported.

Both modes share the character and account/session infrastructure. Quick Practice uses event-specific mood images; Teaching mode currently keeps the default mood.

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

**Limitations:** all 16 topics have validated hybrid parameter proposal paths, but the automated variety checks use fixed test fixtures; live model output quality and syllabus coverage have not been evaluated. This is not an official JEE question bank and should not be represented as JEE Main/Advanced exam coverage.

### Answer shapes

Every problem declares an `answer_shape` (in `schemas.py`), which determines both how `verify.py` checks it and what input widget the frontend renders:

| Shape | Meaning | Status |
|---|---|---|
| `single_value` | one number/fraction | ✅ implemented |
| `multi_value` | a set of valid answers (e.g. quadratic roots) | ✅ implemented |
| `vector_or_matrix` | ordered vector or matrix | ✅ exact element-wise verification |
| `expression` | symbolic antiderivative equivalence, including `+ C` | ✅ implemented for calculus |

Vector/matrix answers use comma-separated values and semicolons between matrix rows. Symbolic equivalence is currently used for polynomial antiderivatives.

### Teaching-mode flow

`routes/chat.py` extracts text from user input or an uploaded image/PDF, attempts a SymPy solution for supported math, and asks the selected persona to explain. It does not use the legacy `chat_tools.py` tool loop. `/hint` is separate: it returns a short LLM-generated hint without submitting an attempt, changing streak, or consuming the active problem.

### Adaptive difficulty

Problems scale from difficulty 1–10 based on streak:
- streak ≥ 5 correct → +2 difficulty
- streak ≥ 3 correct → +1 difficulty
- wrong → −1 difficulty

### Event system (Quick Practice)

Every Quick Practice submit maps to one of 11 event categories:

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
| `give_up_request` | Legacy `give_up=true` submission; the UI hint button no longer forfeits |
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
| v1.4.0 | Sukuna, Makima, and Goku personas; all four characters activated with mood images. Migrated from Hugging Face's router to Groq direct. Fixed reasoning output leakage, tool-schema mismatches, empty replies, persona headers, and topic/category naming collisions. |
| v2.0.0 | Chat mode revamped into teaching mode. Accepts text, image, or PDF. New `extractor.py` (vision model for images, pdfplumber for typed PDFs, PyMuPDF fallback for scanned). New `solver.py` (SymPy-backed teaching solver for equations, derivatives, integrals). `/chat` now accepts multipart form data. `ChatWindow.jsx` gains file upload. No difficulty tracking or mood changes in chat mode. `ChatResponse` simplified (streak/difficulty removed). |
| v2.1.0 | Multi-user foundation completed: JWT authentication with httpOnly cookies, per-user session ownership, PostgreSQL persistence, session history summaries, improved auth UI, direct chat flow without topic selection, conversational intent routing, KaTeX equation rendering, and clearer loading states. Fixed the session-history 500 error caused by a missing SQLAlchemy `Integer` import. |
| v2.2.0 | New pages: `/dashboard`, `/syllabus`, `/history/:sessionId`, `/account`, `/privacy`, `/terms`, `/404`. Profile customization (display name, avatar upload). Persistent top navbar with active-route highlighting, hidden only during active sessions. Fade/slide page transitions that actually work (key on component, not div). Polished pill-style buttons throughout. Dashboard as default post-login page. React Router 7 wired throughout. New backend: `GET /analytics`, `GET /syllabus/progress`, `PATCH /auth/profile`, `POST /auth/profile/avatar`, `GET /sessions/{id}/attempts`, `POST /auth/change-password`, `DELETE /auth/account`. `display_name` + `avatar_url` + `mode` (session) added to DB models with migrations. `delete_user` cascade fixed. Frontend containerized (nginx, multi-stage Docker build). `avatars_data` named volume in docker-compose. `VITE_API_URL` build arg. Fixed: missing `src/data/characters.js` (build crash), missing `PrivacyPage`/`TermsPage` (build crash), `TopNav` null vs undefined check, `startTopic` from SyllabusPage now actually forwards through character/mode to topic selection. |
| v3.0 work in progress | Non-forfeiting hints; correct retry UX for invalid input; four-answer-shape verification; validated LLM-proposed parameters for all 16 topics; deterministic proposal variety and answer-verification tests; session summaries; lazy-loaded chat bundle; configurable CORS. |

---

## Roadmap

### v2.x — Multi-user platform
- [x] v2.0.0 — Chat mode revamped into teaching mode
- [x] v2.1.0 — Auth, PostgreSQL, session ownership, history
- [x] v2.2.0 — Dashboard, Syllabus, account management, React Router, persistent navbar, page transitions, profile customization, Docker frontend, all routing bugs fixed
- [x] Activate all four characters and wire their mood images
- [x] Keep `not_serious` attempts on the same problem in the UI
- [x] Provide hints without forfeiting or recording an attempt
- [x] Persist chat history, active problems, and session progress; restore the active session after API restart or same-tab refresh

### v3.x — Immersive experience *(long-term)*
- [x] `vector_or_matrix` and `expression` verification for generated exercises
- [x] Hybrid parameter proposals for linear equations, quadratics, probability, and statistics; SymPy computes the answers
- [x] Expand validated hybrid parameter generation to all 16 topics; test two distinct proposal fixtures and answer verification per topic
- [ ] Evaluate live model-generated variety, educational quality, and syllabus depth across all topics
- [x] Quick Practice session summaries in history detail
- [ ] Periodic mixed-topic assessments
- [ ] Animated dialogue presentation and optional generic text-to-speech
- [ ] Build an original or properly licensed JEE-style question bank; do not label generated practice as official exam content

---

## Project status and deployment boundary

Validated hybrid generation is wired for all 16 topics. Topic-specific bounded proposal fields are validated, and problem prompts and canonical answers are built by backend code (using SymPy for symbolic calculations). Regression tests show that two distinct valid proposal fixtures per topic produce different prompts and verifiable answers. Session chat history, active problems, and related progress now persist in PostgreSQL; an authenticated resume endpoint restores the active session and never returns the canonical answer. The 26 backend tests cover active-problem JSON round-trips for every topic. This is code-level variety coverage—not a statistical evaluation of live LLM output, educational quality, or full-syllabus/JEE coverage, which remain unfinished.

Docker Compose is prepared for local use; `FRONTEND_URL`, `VITE_API_URL`, and CORS support deployment configuration. The project has **not** been deployed. Hosting, domain, TLS/reverse proxy, managed database, provider OAuth settings, secrets, and production smoke tests still need configuration and verification. Before public release, use only character content and assets authorized for that use. Any future speech feature should use licensed or generic voices, not replicas trained on source recordings.

**Completion verdict:** the project is not finished. The current frontend builds and lint passes, and the focused backend tests pass; v3 features and real production deployment remain in progress.

---

## Environment variables

| Variable | Where | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | repository-root `.env` | Password for the PostgreSQL `tutor` user; Compose uses it to initialize the database and build the container database URL. |
| `DATABASE_URL` | repository-root `.env` for host-run backend | SQLAlchemy PostgreSQL URL. Compose overrides this inside its backend container; for host-run backend, point it at the local PostgreSQL service, e.g. `postgresql+psycopg2://tutor:<password>@localhost:5432/tutor`. |
| `JWT_SECRET_KEY` | repository-root `.env` | Secret used to sign authentication JWTs; generate a unique random value. |
| `SESSION_SECRET_KEY` | repository-root `.env` | Separate secret for OAuth session/CSRF state; generate a different random value. |
| `GOOGLE_CLIENT_ID` | repository-root `.env` | Google OAuth web application client ID; required by backend initialization. |
| `GOOGLE_CLIENT_SECRET` | repository-root `.env` | Secret paired with the Google OAuth client ID. |
| `GOOGLE_REDIRECT_URI` | repository-root `.env` | Must exactly match the OAuth redirect URI registered with Google; local default is `http://localhost:8000/auth/oauth/google/callback`. |
| `GROQ_API_KEY` | repository-root `.env` | Groq API key for direct LLM access (replaces the old `HF_TOKEN`). |
| `FRONTEND_URL` | repository-root `.env` | Browser frontend origin used for OAuth redirects and CORS. Local Docker default: `http://localhost`. |
| `VITE_API_URL` | repository-root `.env` | API URL embedded in the frontend at Docker build time. Local Docker default: `http://localhost:8000`; for a public deployment, use the externally reachable HTTPS API URL. |
| `ENV` | repository-root `.env` | Development/production setting for host-run backend auth cookies. Compose currently sets `ENV=production` in the backend container. |
