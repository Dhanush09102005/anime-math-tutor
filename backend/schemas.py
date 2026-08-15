from enum import Enum
from typing import Optional
from pydantic import BaseModel


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
    answer_shape: AnswerShape


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