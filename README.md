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
│   ├── state.py                  In-memory session store + constants
│   ├── requirements.txt
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

Every submit maps to one of 6 event categories:

| Event | Condition |
|---|---|
| `correct_first_try` | Correct, streak < 3 |
| `correct_streak` | Correct, streak ≥ 3 |
| `incorrect` | Wrong, new mistake type |
| `repeated_mistake` | Wrong, same mistake as last time |
| `give_up_request` | User asked for a hint |
| `topic_mastered` | Correct at difficulty ≥ 8 (once per session) |

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

## Roadmap

### Current (v0.x) — Kakashi vertical slice
- [x] Full problem → answer → LLM reaction loop
- [x] Adaptive difficulty
- [x] Mood-driven character art
- [ ] SQLite persistence (session history survives server restart)

### v1.0 — Reliable learning tool
- Improved Kakashi response quality
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
