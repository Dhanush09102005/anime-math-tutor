import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from routes import auth, session, problem, submit, chat

app = FastAPI(title="Anime Math Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # already required for the JWT cookie auth uses
)

# Required by Authlib to hold OAuth CSRF state/nonce between the redirect to
# Google and the callback — a separate signed cookie from our own JWT auth
# cookie (COOKIE_NAME in auth/dependencies.py), different purpose entirely.
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET_KEY"])

app.include_router(auth.router)
app.include_router(session.router)
app.include_router(problem.router)
app.include_router(submit.router)
app.include_router(chat.router)

# NOTE: no more init_db() on startup. Schema is owned by Alembic now —
# run `alembic upgrade head` before starting the app (docker-compose's
# backend command does this automatically; for local dev without Docker,
# run it manually once against your local Postgres).


@app.get("/health")
def health():
    import state
    return {"status": "ok", "active_sessions": len(state.SESSIONS)}
