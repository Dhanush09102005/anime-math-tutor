import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.dependencies import get_admin_user, get_current_user
from db.database import get_db
from db.models import PaperAttempt, QuestionPaper, User
from schemas import PaperAnswerRequest, QuestionPaperCreateRequest

router = APIRouter(prefix="/question-banks", tags=["question banks"])


def _public_questions(paper: QuestionPaper) -> list[dict]:
    return [
        {
            "prompt": question["prompt"],
            "question_type": question["question_type"],
            "options": question.get("options", []),
        }
        for question in paper.questions
    ]


def _get_paper(paper_id: uuid.UUID, db: Session) -> QuestionPaper:
    paper = db.query(QuestionPaper).filter(QuestionPaper.id == paper_id).first()
    if paper is None:
        raise HTTPException(status_code=404, detail="Question paper not found.")
    return paper


def _get_attempt(attempt_id: uuid.UUID, user_id: uuid.UUID, db: Session) -> PaperAttempt:
    attempt = db.query(PaperAttempt).filter(PaperAttempt.id == attempt_id).first()
    if attempt is None:
        raise HTTPException(status_code=404, detail="Question paper attempt not found.")
    if attempt.user_id != user_id:
        raise HTTPException(status_code=403, detail="This attempt belongs to another user.")
    return attempt


@router.get("")
def list_question_papers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    papers = db.query(QuestionPaper).order_by(QuestionPaper.created_at.desc()).all()
    attempts = (
        db.query(PaperAttempt)
        .filter(PaperAttempt.user_id == current_user.id)
        .order_by(PaperAttempt.started_at.desc())
        .all()
    )
    attempts_by_paper: dict[uuid.UUID, list[PaperAttempt]] = {}
    for attempt in attempts:
        attempts_by_paper.setdefault(attempt.paper_id, []).append(attempt)

    results = []
    for paper in papers:
        paper_attempts = attempts_by_paper.get(paper.id, [])
        completed = [attempt for attempt in paper_attempts if attempt.completed_at is not None]
        in_progress = next(
            (attempt for attempt in paper_attempts if attempt.completed_at is None),
            None,
        )
        results.append(
            {
                "id": str(paper.id),
                "title": paper.title,
                "description": paper.description,
                "topic": paper.topic,
                "question_count": len(paper.questions),
                "created_at": paper.created_at.isoformat(),
                "best_score": max((attempt.score for attempt in completed), default=None),
                "completed_count": len(completed),
                "in_progress_attempt_id": str(in_progress.id) if in_progress else None,
            }
        )
    return results


@router.post("", status_code=201)
def create_question_paper(
    request: QuestionPaperCreateRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    questions = [
        question.model_dump()
        for question in request.questions
    ]
    paper = QuestionPaper(
        title=request.title.strip(),
        description=request.description.strip(),
        topic=request.topic.strip(),
        questions=questions,
        created_by=admin.id,
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return {"id": str(paper.id), "title": paper.title}


@router.get("/admin/progress")
def list_student_progress(
    _admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(PaperAttempt, User, QuestionPaper)
        .join(User, PaperAttempt.user_id == User.id)
        .join(QuestionPaper, PaperAttempt.paper_id == QuestionPaper.id)
        .order_by(PaperAttempt.started_at.desc())
        .all()
    )
    return [
        {
            "attempt_id": str(attempt.id),
            "student_email": user.email,
            "paper_title": paper.title,
            "score": attempt.score,
            "correct_count": attempt.correct_count,
            "question_count": len(paper.questions),
            "started_at": attempt.started_at.isoformat(),
            "completed_at": attempt.completed_at.isoformat() if attempt.completed_at else None,
        }
        for attempt, user, paper in rows
    ]


@router.get("/attempts/{attempt_id}")
def get_paper_attempt(
    attempt_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = _get_attempt(attempt_id, current_user.id, db)
    paper = _get_paper(attempt.paper_id, db)
    result = {
        "attempt_id": str(attempt.id),
        "paper": {
            "id": str(paper.id),
            "title": paper.title,
            "description": paper.description,
            "topic": paper.topic,
            "questions": _public_questions(paper),
        },
        "answers": attempt.answers,
        "completed": attempt.completed_at is not None,
        "score": attempt.score,
        "correct_count": attempt.correct_count,
    }
    if attempt.completed_at is not None:
        result["results"] = [
            {
                **question,
                "submitted_answer": attempt.answers[index],
                "correct": _normalize_answer(attempt.answers[index])
                in {_normalize_answer(value) for value in question["accepted_answers"]},
            }
            for index, question in enumerate(paper.questions)
        ]
    return result


@router.put("/attempts/{attempt_id}/answers")
def save_paper_answers(
    attempt_id: uuid.UUID,
    request: PaperAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = _get_attempt(attempt_id, current_user.id, db)
    if attempt.completed_at is not None:
        raise HTTPException(status_code=409, detail="This paper has already been submitted.")

    paper = _get_paper(attempt.paper_id, db)
    if len(request.answers) != len(paper.questions):
        raise HTTPException(
            status_code=400,
            detail=f"Save one answer slot for each of the {len(paper.questions)} questions.",
        )

    attempt.answers = request.answers
    db.commit()
    return {"saved": True}


def _normalize_answer(answer: str) -> str:
    return " ".join(answer.split()).casefold()


@router.get("/{paper_id}")
def get_question_paper(
    paper_id: uuid.UUID,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    paper = _get_paper(paper_id, db)
    return {
        "id": str(paper.id),
        "title": paper.title,
        "description": paper.description,
        "topic": paper.topic,
        "questions": _public_questions(paper),
    }


@router.post("/{paper_id}/attempts", status_code=201)
def start_paper_attempt(
    paper_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_paper(paper_id, db)
    existing = (
        db.query(PaperAttempt)
        .filter(
            PaperAttempt.paper_id == paper_id,
            PaperAttempt.user_id == current_user.id,
            PaperAttempt.completed_at.is_(None),
        )
        .order_by(PaperAttempt.started_at.desc())
        .first()
    )
    if existing is not None:
        return {"attempt_id": str(existing.id)}

    attempt = PaperAttempt(paper_id=paper_id, user_id=current_user.id, answers=[])
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return {"attempt_id": str(attempt.id)}


@router.post("/attempts/{attempt_id}/submit")
def submit_paper_answers(
    attempt_id: uuid.UUID,
    request: PaperAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    attempt = _get_attempt(attempt_id, current_user.id, db)
    if attempt.completed_at is not None:
        raise HTTPException(status_code=409, detail="This paper has already been submitted.")

    paper = _get_paper(attempt.paper_id, db)
    if len(request.answers) != len(paper.questions):
        raise HTTPException(
            status_code=400,
            detail=f"Submit one answer for each of the {len(paper.questions)} questions.",
        )

    normalized_answers = [_normalize_answer(answer) for answer in request.answers]
    correct = [
        answer in {_normalize_answer(value) for value in question["accepted_answers"]}
        for answer, question in zip(normalized_answers, paper.questions)
    ]
    correct_count = sum(correct)
    score = round(correct_count * 100 / len(paper.questions))

    attempt.answers = request.answers
    attempt.correct_count = correct_count
    attempt.score = score
    attempt.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "score": score,
        "correct_count": correct_count,
        "question_count": len(paper.questions),
        "results": [
            {
                "prompt": question["prompt"],
                "submitted_answer": request.answers[index],
                "correct_answer": question["accepted_answers"][0],
                "correct": correct[index],
            }
            for index, question in enumerate(paper.questions)
        ],
    }
