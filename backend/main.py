from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import session, problem, submit
from db.database import init_db

app = FastAPI(title="Anime Math Tutor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(session.router)
app.include_router(problem.router)
app.include_router(submit.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    import state
    return {"status": "ok", "active_sessions": len(state.SESSIONS)}