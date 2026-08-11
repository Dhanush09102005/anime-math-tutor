from typing import Optional
from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    persona_id: str


class CreateSessionResponse(BaseModel):
    session_id: str
    persona_id: str
    topic: str
    difficulty: int


class ProblemRequest(BaseModel):
    session_id: str
    topic: Optional[str] = None


class ProblemResponse(BaseModel):
    problem_id: str
    topic: str
    difficulty: int
    prompt_text: str


class SubmitRequest(BaseModel):
    session_id: str
    problem_id: str
    answer: Optional[str] = None
    give_up: bool = False


class SubmitResponse(BaseModel):
    correct: bool
    mistake_type: Optional[str]
    correct_answer: str
    event_category: str
    reaction: str
    streak: int
    difficulty: int