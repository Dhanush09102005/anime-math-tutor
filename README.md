# Anime Math Tutor

An adaptive math tutor where anime characters teach you — in character. Pick a sensei, solve problems, and get real-time LLM-generated reactions in their voice. Currently featuring **Kakashi Hatake**.

---

## Demo

> Select Kakashi → solve a linear equation → get roasted (or mildly praised) in his exact voice

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
│   ├── schemas.py                Pydantic request/response models
│   ├── state.py                  Session cache + constants
│   ├── requirements.txt
│   ├── tutor.db                  SQLite database (gitignored)
│   ├── db/
│   │   └── database.py           Schema, init, session + attempt CRUD
│   ├── math_engine/
│   │   ├── generate.py           Problem generation (SymPy)
│   │   ├── verify.py             Answer parsing + mistake classification
│   │   └── difficulty.py        Adaptive difficulty logic
│   ├── personas/
│   │   ├── kakashi.json          Kakashi persona config
│   │   └── prompt_builder.py    Event classifier + LLM prompt assembler
│   ├── llm_client/
│   │   └── hf_client.py         HuggingFace router → Llama 3.3 70B
│   └── routes/
│       ├── session.py            POST /session
│       ├── problem.py            POST /problem
│       └── submit.py             POST /submit
│
└── anime-tutor/
    └── src/
        ├── App.jsx               Phase state machine
        ├── api/client.js         Fetch wrapper for all 3 endpoints
        ├── components/
        │   ├── CharacterSelect.jsx
        │   ├── CharacterPanel.jsx   Left-half mood image
        │   ├── SessionHeader.jsx    Streak + mission rank
        │   ├── ProblemCard.jsx
        │   └── ReactionPanel.jsx   Typewriter reaction display
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

---

## How it works

Three API calls drive the entire app:

```
POST /session   { persona_id }           → session_id
POST /problem   { session_id }           → problem text + difficulty
POST /submit    { session_id, answer }   → correct/wrong + LLM reaction
```

The backend never sends the answer to the frontend. Verification is server-side only.

### Adaptive difficulty

Problems scale from difficulty 1–10 based on streak:
- streak ≥ 5 correct → +2 difficulty
- streak ≥ 3 correct → +1 difficulty
- wrong → −1 difficulty

### Event system

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
| `not_serious` | Non-numeric or expression input |

The event category drives both the LLM prompt and the character's mood image simultaneously — they can never disagree.

### Persona system

Each character is a JSON file in `backend/personas/`. The LLM is given the character's philosophy, tone, speech patterns, and an example reaction line for the current event — then generates a fresh response. Nothing is hardcoded.

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

## Version history

| Version | What landed |
|---|---|
| v0.1.0 | math_engine core (generate / verify / difficulty) + React + Vite frontend scaffold |
| v0.1.1 | Kakashi persona JSON + prompt_builder complete, pipeline tested in isolation |
| v0.2.0 | Full LLM integration — end-to-end pipeline proven live via REPL (generate → verify → classify → prompt → real Llama 3.3 70B call → in-character response) |
| v0.3.0 | FastAPI layer: `/session`, `/problem`, `/submit` wired over HTTP; router pattern (main.py, schemas.py, state.py, routes/); tested via Swagger |
| v0.4.0 | React frontend: CharacterSelect, CharacterPanel, SessionHeader, ProblemCard, ReactionPanel, mood-image system tied to event categories, api/client.js |
| v1.0.0 | SQLite persistence (backend/db/), `not_serious` event, verify.py fixes, README — completes the vertical slice |
| v1.0.1 | Hotfix: `-05` now correctly accepted as `-5` (leading-zero normalisation before SymPy parse) |

---

## Roadmap

### v1.x — Improving Kakashi + expanding content
- Improved Kakashi LLM response quality
- More math topics: calculus, trigonometry, linear algebra, probability & statistics
- Topic/subtopic selection + mixed question bank
- Sukuna, Makima, Mahito added to same depth as Kakashi
- Per-character theming and frontend improvements

### v2.0 — Multi-user platform
- Authentication, user accounts
- Per-user progress, analytics, history
- Full database, multiple pages, proper routing

### v3.0 — Immersive experience *(long-term)*
- Animated characters, voice acting trained on source material
- Dialogue-box UI, doubt-solving chat, session summaries
- JEE Mains + Advanced question bank replacing procedural generation

---

## Environment variables

| Variable | Where | Description |
|---|---|---|
| `HF_TOKEN` | `backend/.env` | HuggingFace API token for LLM access |
