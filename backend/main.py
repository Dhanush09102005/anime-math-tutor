import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from routes import auth, session, problem, submit, chat, analytics

app = FastAPI(title="Anime Math Tutor API")

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
allowed_origins = {
    frontend_url,
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:80",
    "http://127.0.0.1:80",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(allowed_origins),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # already required for the JWT cookie auth uses
)

# Required by Authlib to hold OAuth CSRF state/nonce between the redirect to
# Google and the callback — a separate signed cookie from our own JWT auth
# cookie (COOKIE_NAME in auth/dependencies.py), different purpose entirely.
app.add_middleware(SessionMiddleware, secret_key=os.environ["SESSION_SECRET_KEY"])

# Serves uploaded avatars back out at /static/avatars/<file> — this was the
# "unmounted avatar static files" gap noted in CONTEXT.md. routes/auth.py's
# profile-avatar upload writes into static/avatars/, so this mount has to
# point at the same "static" directory or uploads 404 on read.
os.makedirs("static/avatars", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(auth.router)
app.include_router(session.router)
app.include_router(problem.router)
app.include_router(submit.router)
app.include_router(chat.router)
app.include_router(analytics.router)

# NOTE: no more init_db() on startup. Schema is owned by Alembic now —
# run `alembic upgrade head` before starting the app (docker-compose's
# backend command does this automatically; for local dev without Docker,
# run it manually once against your local Postgres).


@app.get("/health")
def health():
    import state
    return {"status": "ok", "active_sessions": len(state.SESSIONS)}
