import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from auth.dependencies import get_admin_user, is_admin
from db.models import PaperAttempt, QuestionPaper
from routes import question_banks
from schemas import PaperAnswerRequest, PaperQuestionInput, QuestionPaperCreateRequest


def test_admin_email_configuration_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "teacher@example.com, owner@example.com")
    user = SimpleNamespace(email="Teacher@Example.com")

    assert is_admin(user)
    assert get_admin_user(user) is user
    assert not is_admin(SimpleNamespace(email="student@example.com"))


def test_paper_question_validation_requires_correct_multiple_choice_option():
    with pytest.raises(ValidationError, match="Each accepted answer must match one of the options"):
        PaperQuestionInput(
            prompt="What is 2 + 2?",
            question_type="multiple_choice",
            options=["3", "4"],
            accepted_answers=["5"],
        )


def test_short_answer_questions_reject_options():
    with pytest.raises(ValidationError, match="Short-answer questions cannot include"):
        PaperQuestionInput(
            prompt="What is 2 + 2?",
            question_type="short_answer",
            options=["4"],
            accepted_answers=["4"],
        )


def test_question_paper_requires_at_least_one_question():
    with pytest.raises(ValidationError):
        QuestionPaperCreateRequest(title="Empty", topic="Numbers", questions=[])


def test_public_question_data_never_contains_answer_keys():
    paper = SimpleNamespace(
        questions=[
            {
                "prompt": "What is 2 + 2?",
                "question_type": "multiple_choice",
                "options": ["3", "4"],
                "accepted_answers": ["4"],
            }
        ]
    )

    assert question_banks._public_questions(paper) == [
        {
            "prompt": "What is 2 + 2?",
            "question_type": "multiple_choice",
            "options": ["3", "4"],
        }
    ]


def test_attempt_lookup_rejects_another_users_attempt():
    owner_id = uuid.uuid4()
    attempt = SimpleNamespace(user_id=owner_id)

    class Query:
        def filter(self, _condition):
            return self

        def first(self):
            return attempt

    class Database:
        def query(self, _model):
            return Query()

    with pytest.raises(HTTPException) as error:
        question_banks._get_attempt(uuid.uuid4(), uuid.uuid4(), Database())

    assert error.value.status_code == 403


def test_submit_paper_answers_grades_and_persists_attempt():
    user_id = uuid.uuid4()
    attempt = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        paper_id=uuid.uuid4(),
        completed_at=None,
        answers=[],
        score=None,
        correct_count=None,
    )
    paper = SimpleNamespace(
        id=attempt.paper_id,
        questions=[
            {"prompt": "Choose four", "accepted_answers": ["4"]},
            {"prompt": "Name the number", "accepted_answers": ["two", "2"]},
        ],
    )

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, _condition):
            return self

        def first(self):
            return self.result

    class Database:
        committed = False

        def query(self, model):
            return Query(attempt if model is PaperAttempt else paper)

        def commit(self):
            self.committed = True

    db = Database()
    result = question_banks.submit_paper_answers(
        attempt.id,
        PaperAnswerRequest(answers=[" 4 ", "TWO"]),
        SimpleNamespace(id=user_id),
        db,
    )

    assert result["score"] == 100
    assert result["correct_count"] == 2
    assert attempt.answers == [" 4 ", "TWO"]
    assert attempt.completed_at is not None
    assert db.committed


def test_saving_draft_persists_answers_without_completing_attempt():
    user_id = uuid.uuid4()
    attempt = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=user_id,
        paper_id=uuid.uuid4(),
        completed_at=None,
        answers=[],
    )
    paper = SimpleNamespace(id=attempt.paper_id, questions=[{}, {}])

    class Query:
        def __init__(self, result):
            self.result = result

        def filter(self, _condition):
            return self

        def first(self):
            return self.result

    class Database:
        committed = False

        def query(self, model):
            return Query(attempt if model is PaperAttempt else paper)

        def commit(self):
            self.committed = True

    db = Database()
    result = question_banks.save_paper_answers(
        attempt.id,
        PaperAnswerRequest(answers=["4", ""]),
        SimpleNamespace(id=user_id),
        db,
    )

    assert result == {"saved": True}
    assert attempt.answers == ["4", ""]
    assert attempt.completed_at is None
    assert db.committed


def test_admin_progress_route_precedes_dynamic_paper_route():
    paths = [route.path for route in question_banks.router.routes]

    assert paths.index("/question-banks/admin/progress") < paths.index("/question-banks/{paper_id}")
