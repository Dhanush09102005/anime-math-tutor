from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class AnswerShape(str, Enum):
    """
    Declares what kind of answer a problem expects. Set by the generator that
    creates the problem (generate.py) — never inferred at runtime, since the
    shape is a property of the specific question asked, not the numbers in it.

    Drives two things downstream:
      - verify_answer() dispatches to a shape-specific SymPy checker
      - the frontend picks the matching input widget
    """
    SINGLE_VALUE = "single_value"          # one number/fraction — e.g. linear equations, definite integrals, determinants
    MULTI_VALUE = "multi_value"            # a set of valid answers — e.g. quadratic roots, trig solve-on-interval
    VECTOR_OR_MATRIX = "vector_or_matrix"  # ordered tuple/grid — e.g. vectors, matrix results
    EXPRESSION = "expression"              # symbolic equivalence — e.g. equation of a line/circle, indefinite integrals, DEs


# ── Auth ───────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    has_password: bool = False
    is_admin: bool = False


class UpdateProfileRequest(BaseModel):
    display_name: Optional[str] = None


# ── Session / problem / submit / chat (unchanged from v2.0.0) ──────────────────

class CreateSessionRequest(BaseModel):
    persona_id: str
    mode: str = "qna"  # "qna" | "chat" — v2.2 chat mode alongside the existing Q&A flow
    topic: Optional[str] = None  # chat mode needs a topic from the start; qna mode still sets it later via /problem


class CreateSessionResponse(BaseModel):
    session_id: str
    persona_id: str
    topic: str
    difficulty: int
    mode: str


class SessionHistoryItem(BaseModel):
    session_id: str
    persona_id: str
    topic: str
    mode: str
    difficulty: int
    streak: int
    attempt_count: int
    correct_count: int
    created_at: str


class AttemptItem(BaseModel):
    id: int
    problem_id: str
    topic: str
    difficulty: int
    correct: bool
    mistake_type: Optional[str]
    event_category: str
    timestamp: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ProblemRequest(BaseModel):
    session_id: str
    topic: Optional[str] = None


class ProblemResponse(BaseModel):
    problem_id: str
    topic: str
    difficulty: int
    prompt_text: str
    answer_shape: AnswerShape
    generation_mode: str = "procedural"


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SessionResumeResponse(BaseModel):
    session_id: str
    persona_id: str
    mode: str
    topic: str
    difficulty: int
    streak: int
    active_problem: Optional[ProblemResponse] = None
    conversation_history: list[ChatHistoryMessage] = Field(default_factory=list)


class PaperQuestionInput(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    question_type: Literal["multiple_choice", "short_answer"]
    options: list[str] = Field(default_factory=list, max_length=8)
    accepted_answers: list[str] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def validate_question(self):
        if not self.prompt.strip() or any(not option.strip() for option in self.options):
            raise ValueError("Question text and options cannot be blank.")
        if any(not answer.strip() for answer in self.accepted_answers):
            raise ValueError("Accepted answers cannot be blank.")
        if self.question_type == "multiple_choice":
            if len(self.options) < 2:
                raise ValueError("Multiple-choice questions need at least two options.")
            normalized_options = {option.strip().casefold() for option in self.options}
            if any(answer.strip().casefold() not in normalized_options for answer in self.accepted_answers):
                raise ValueError("Each accepted answer must match one of the options.")
        elif self.options:
            raise ValueError("Short-answer questions cannot include multiple-choice options.")
        return self


class QuestionPaperCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    topic: str = Field(min_length=1, max_length=100)
    questions: list[PaperQuestionInput] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_paper(self):
        if not self.title.strip() or not self.topic.strip():
            raise ValueError("Paper title and topic cannot be blank.")
        return self


class PaperAnswerRequest(BaseModel):
    answers: list[str] = Field(max_length=100)


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


class HintRequest(BaseModel):
    session_id: str
    problem_id: str


class HintResponse(BaseModel):
    hint: str


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str
    mood: str = "default"  # teaching mode always uses default — no mood tracking
