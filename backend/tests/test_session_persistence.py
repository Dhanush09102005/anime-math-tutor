import asyncio
from types import SimpleNamespace

import pytest
import sympy as sp

import state
from db import crud
from db.models import SessionModel
from db.session_state import deserialize_active_problem, serialize_active_problem
import routes.chat as chat_route
import routes.session as session_route
import routes.submit as submit_route
from routes.session import get_session
from schemas import AnswerShape, SubmitRequest


@pytest.mark.parametrize(
    "canonical_answer,answer_shape",
    [
        (sp.Rational(3, 8), AnswerShape.SINGLE_VALUE),
        ([sp.Integer(-2), sp.Integer(4)], AnswerShape.MULTI_VALUE),
        (sp.Matrix([[sp.Rational(1, 2), -3], [0, 7]]), AnswerShape.VECTOR_OR_MATRIX),
        (sp.integrate(3 * sp.Symbol("x") ** 2, sp.Symbol("x")), AnswerShape.EXPRESSION),
        ([sp.pi / 6, 5 * sp.pi / 6], AnswerShape.MULTI_VALUE),
    ],
)
def test_active_problem_round_trips_sympy_answers(canonical_answer, answer_shape):
    problem = {
        "id": "problem-1",
        "topic": "test_topic",
        "difficulty": 3,
        "prompt_text": "Test prompt",
        "generation_mode": "procedural",
        "answer_shape": answer_shape,
        "canonical_answer": canonical_answer,
        "equation": sp.Eq(sp.Symbol("x") + 1, 2),
    }

    restored = deserialize_active_problem(serialize_active_problem(problem))

    assert restored == {
        "id": "problem-1",
        "topic": "test_topic",
        "difficulty": 3,
        "prompt_text": "Test prompt",
        "generation_mode": "procedural",
        "answer_shape": answer_shape,
        "canonical_answer": canonical_answer,
    }


def test_load_session_restores_runtime_state_after_cache_miss(monkeypatch):
    user_id = object()
    active_problem = {
        "id": "problem-1",
        "topic": "linear_equations",
        "difficulty": 2,
        "prompt_text": "Solve for x: x + 1 = 3",
        "generation_mode": "hybrid",
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(2),
    }
    row = SimpleNamespace(
        user_id=user_id,
        persona_id="kakashi",
        topic="linear_equations",
        mode="qna",
        difficulty=2,
        streak=4,
        mastery_announced=False,
        last_mistake_type=None,
        current_problem=serialize_active_problem(active_problem),
        conversation_history=[
            {"role": "user", "content": "Can you explain that?"},
            {"role": "assistant", "content": "Let's look at the first step."},
        ],
        consecutive_wrong=1,
    )

    class Query:
        def filter(self, _condition):
            return self

        def first(self):
            return row

    class Database:
        def query(self, _model):
            assert _model is SessionModel
            return Query()

    monkeypatch.setattr(state, "SESSIONS", {})
    restored = get_session("session-1", SimpleNamespace(id=user_id), Database())

    assert restored["current_problem"] == active_problem
    assert restored["conversation_history"] == row.conversation_history
    assert restored["consecutive_wrong"] == 1
    assert state.SESSIONS["session-1"] is restored


def test_update_session_persists_all_resumable_state():
    updates = {}

    class Query:
        def filter(self, _condition):
            return self

        def update(self, values):
            updates.update(values)

    class Database:
        def query(self, _model):
            assert _model is SessionModel
            return Query()

        def commit(self):
            self.committed = True

    active_problem = {
        "id": "problem-1",
        "topic": "calculus",
        "difficulty": 2,
        "prompt_text": "Find an antiderivative of 3x^2",
        "answer_shape": AnswerShape.EXPRESSION,
        "canonical_answer": sp.Symbol("x") ** 3,
    }
    history = [{"role": "assistant", "content": "Welcome back."}]
    db = Database()

    crud.update_session(
        db,
        session_id="session-1",
        difficulty=2,
        streak=1,
        mastery_announced=False,
        last_mistake_type=None,
        topic="calculus",
        current_problem=active_problem,
        conversation_history=history,
        consecutive_wrong=0,
    )

    assert updates["current_problem"] == serialize_active_problem(active_problem)
    assert updates["conversation_history"] == history
    assert updates["consecutive_wrong"] == 0
    assert db.committed is True


def test_active_problem_serializer_rejects_unsupported_sympy_nodes():
    problem = {
        "id": "problem-1",
        "topic": "test_topic",
        "difficulty": 1,
        "prompt_text": "Test",
        "answer_shape": AnswerShape.EXPRESSION,
        "canonical_answer": sp.Integral(sp.Symbol("x"), sp.Symbol("x")),
    }

    with pytest.raises(TypeError, match="Unsupported symbolic value"):
        serialize_active_problem(problem)


def test_chat_turn_is_saved_to_session_state(monkeypatch):
    session = {
        "persona_id": "kakashi",
        "mode": "chat",
        "difficulty": 2,
        "streak": 1,
        "mastery_announced": False,
        "last_mistake_type": None,
        "topic": "linear_equations",
        "current_problem": None,
        "conversation_history": [],
        "consecutive_wrong": 0,
    }
    saved_state = {}
    monkeypatch.setattr(chat_route, "get_session", lambda *_: session)
    monkeypatch.setattr(chat_route, "load_persona", lambda _persona: {"name": "Kakashi"})
    monkeypatch.setattr(chat_route, "build_chat_system_prompt", lambda _persona: "system")
    monkeypatch.setattr(chat_route, "get_teaching_reply", lambda *_: "Let's start with x.")
    monkeypatch.setattr(
        chat_route.crud,
        "update_session",
        lambda _db, **values: saved_state.update(values),
    )

    response = asyncio.run(
        chat_route.chat(
            session_id="session-1",
            message="Can you help me?",
            file=None,
            current_user=object(),
            db=object(),
        )
    )

    expected_history = [
        {"role": "user", "content": "Can you help me?"},
        {"role": "assistant", "content": "Let's start with x."},
    ]
    assert response.reply == "Let's start with x."
    assert session["conversation_history"] == expected_history
    assert saved_state["conversation_history"] == expected_history


def test_resume_endpoint_returns_public_problem_without_answer(monkeypatch):
    session = {
        "persona_id": "kakashi",
        "mode": "qna",
        "topic": "linear_equations",
        "difficulty": 2,
        "streak": 1,
        "current_problem": {
            "id": "problem-1",
            "topic": "linear_equations",
            "difficulty": 2,
            "prompt_text": "Solve for x: x + 1 = 3",
            "generation_mode": "hybrid",
            "answer_shape": AnswerShape.SINGLE_VALUE,
            "canonical_answer": sp.Integer(2),
        },
        "conversation_history": [{"role": "user", "content": "answer is 2"}],
    }
    monkeypatch.setattr(session_route, "get_session", lambda *_: session)

    response = session_route.resume_session(
        "session-1",
        current_user=object(),
        db=object(),
    )

    assert response.active_problem.problem_id == "problem-1"
    assert response.active_problem.generation_mode == "hybrid"
    assert not hasattr(response.active_problem, "canonical_answer")
    assert response.conversation_history == []


def test_resume_endpoint_restores_chat_messages(monkeypatch):
    history = [
        {"role": "user", "content": "What is a derivative?"},
        {"role": "assistant", "content": "It measures the rate of change."},
    ]
    session = {
        "persona_id": "kakashi",
        "mode": "chat",
        "topic": "calculus",
        "difficulty": 1,
        "streak": 0,
        "current_problem": None,
        "conversation_history": history,
    }
    monkeypatch.setattr(session_route, "get_session", lambda *_: session)

    response = session_route.resume_session(
        "session-1",
        current_user=object(),
        db=object(),
    )

    assert [message.model_dump() for message in response.conversation_history] == history


@pytest.mark.parametrize(
    ("answer", "active_after_submit", "attempt_logged"),
    [
        ("?", True, False),
        ("3", False, True),
    ],
)
def test_submit_persists_history_and_active_problem_state(
    monkeypatch,
    answer,
    active_after_submit,
    attempt_logged,
):
    problem = {
        "id": "problem-1",
        "topic": "linear_equations",
        "difficulty": 2,
        "prompt_text": "Solve for x: x + 1 = 4",
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(3),
    }
    session = {
        "persona_id": "kakashi",
        "topic": "linear_equations",
        "mode": "qna",
        "difficulty": 2,
        "streak": 0,
        "consecutive_wrong": 0,
        "mastery_announced": False,
        "last_mistake_type": None,
        "current_problem": problem,
        "conversation_history": [],
    }
    saved_state = {}
    attempts = []
    monkeypatch.setattr(submit_route, "get_session", lambda *_: session)
    monkeypatch.setattr(submit_route, "load_persona", lambda _persona: {"name": "Kakashi"})
    monkeypatch.setattr(submit_route, "build_system_prompt", lambda _persona: "system")
    monkeypatch.setattr(submit_route, "build_turn", lambda **_kwargs: "Solve carefully.")
    monkeypatch.setattr(submit_route, "get_reaction", lambda *_: "Good work.")
    monkeypatch.setattr(
        submit_route.crud,
        "update_session",
        lambda _db, **values: saved_state.update(values),
    )
    monkeypatch.setattr(
        submit_route.crud,
        "log_attempt",
        lambda *_args, **_kwargs: attempts.append(True),
    )

    submit_route.submit_answer(
        SubmitRequest(session_id="session-1", problem_id="problem-1", answer=answer),
        current_user=object(),
        db=object(),
    )

    assert (saved_state["current_problem"] is not None) is active_after_submit
    assert (len(attempts) == 1) is attempt_logged
    assert saved_state["conversation_history"][-1] == {
        "role": "assistant",
        "content": "Good work.",
    }
