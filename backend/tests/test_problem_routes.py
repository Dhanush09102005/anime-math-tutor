import pytest
from fastapi import HTTPException

import httpx
from openai import APIError

import routes.problem as problem_route
import routes.submit as submit_route
from schemas import HintRequest, ProblemRequest


def test_hybrid_problem_response_hides_canonical_answer(monkeypatch):
    session = {
        "topic": "linear_equations",
        "difficulty": 2,
        "streak": 0,
        "mastery_announced": False,
        "last_mistake_type": None,
        "current_problem": None,
        "conversation_history": [],
        "consecutive_wrong": 0,
    }
    monkeypatch.setattr(problem_route, "get_session", lambda *_: session)
    monkeypatch.setattr(
        problem_route,
        "propose_problem_parameters",
        lambda *_: {"a": 3, "b": -4, "solution": 5},
    )
    monkeypatch.setattr(problem_route.crud, "update_session", lambda *_args, **_kwargs: None)

    response = problem_route.get_problem(
        ProblemRequest(session_id="session-1"),
        current_user=object(),
        db=object(),
    )

    assert response.generation_mode == "hybrid"
    assert response.answer_shape == "single_value"
    assert not hasattr(response, "canonical_answer")
    assert session["current_problem"]["canonical_answer"] == 5
    assert session["current_problem"]["id"] == response.problem_id


def test_problem_generation_falls_back_when_ai_proposal_fails(monkeypatch):
    session = {
        "topic": "numbers",
        "difficulty": 2,
        "streak": 0,
        "mastery_announced": False,
        "last_mistake_type": None,
        "current_problem": None,
        "conversation_history": [],
        "consecutive_wrong": 0,
    }
    monkeypatch.setattr(problem_route, "get_session", lambda *_: session)

    def fail_proposal(*_args):
        raise APIError(
            "AI returned invalid JSON",
            request=httpx.Request("POST", "https://example.test"),
            body={"error": "json_validate_failed"},
        )

    monkeypatch.setattr(problem_route, "propose_problem_parameters", fail_proposal)
    monkeypatch.setattr(problem_route.crud, "update_session", lambda *_args, **_kwargs: None)

    response = problem_route.get_problem(
        ProblemRequest(session_id="session-1"),
        current_user=object(),
        db=object(),
    )

    assert response.generation_mode == "procedural_fallback"
    assert "remainder" in response.prompt_text
    assert session["current_problem"]["canonical_answer"] is not None


def test_hint_does_not_consume_or_mutate_active_problem(monkeypatch):
    session = {
        "persona_id": "kakashi",
        "current_problem": {"id": "problem-1", "prompt_text": "Solve x + 2 = 5"},
        "conversation_history": [],
        "streak": 3,
    }
    monkeypatch.setattr(submit_route, "get_session", lambda *_: session)
    monkeypatch.setattr(submit_route, "load_persona", lambda _persona: {"name": "Kakashi"})
    monkeypatch.setattr(submit_route, "build_chat_system_prompt", lambda _persona: "system prompt")
    monkeypatch.setattr(
        submit_route,
        "get_teaching_reply",
        lambda *_: "Isolate x by undoing the addition first.",
    )

    response = submit_route.request_hint(
        HintRequest(session_id="session-1", problem_id="problem-1"),
        current_user=object(),
        db=object(),
    )

    assert response.hint.startswith("Isolate x")
    assert session["current_problem"]["id"] == "problem-1"
    assert session["conversation_history"] == []
    assert session["streak"] == 3


def test_hint_rejects_stale_problem_id(monkeypatch):
    session = {
        "persona_id": "kakashi",
        "current_problem": {"id": "problem-1", "prompt_text": "Solve x + 2 = 5"},
    }
    monkeypatch.setattr(submit_route, "get_session", lambda *_: session)

    with pytest.raises(HTTPException) as error:
        submit_route.request_hint(
            HintRequest(session_id="session-1", problem_id="old-problem"),
            current_user=object(),
            db=object(),
        )

    assert error.value.status_code == 409
