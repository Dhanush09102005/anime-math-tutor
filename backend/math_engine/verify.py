import sympy as sp
from sympy import symbols, sympify
from sympy.parsing.sympy_parser import parse_expr

x = symbols('x')

def verify_answer(problem: dict, user_answer: str) -> dict:
    """
    Verifies a user's answer against a problem's canonical_answer.

    Args:
        problem: dict returned by generate_problem() — must contain "canonical_answer"
        user_answer: raw string typed by the user, e.g. "5", "x=5", "5.0"

    Returns:
        {
            "correct": bool,
            "parsed_answer": sympy expr or None,
            "mistake_type": str or None   # "unparseable", "sign_error", "wrong", None if correct
        }
    """
    canonical = problem["canonical_answer"]

    parsed = _parse_user_answer(user_answer)

    if parsed is None:
        return {
            "correct": False,
            "parsed_answer": None,
            "mistake_type": "unparseable",
        }

    if parsed == canonical:
        return {
            "correct": True,
            "parsed_answer": parsed,
            "mistake_type": None,
        }

    # Wrong — try to classify *how* it's wrong before falling back to generic "wrong"
    mistake_type = _classify_mistake(parsed, canonical)

    return {
        "correct": False,
        "parsed_answer": parsed,
        "mistake_type": mistake_type,
    }


def _parse_user_answer(raw: str):
    if raw is None:
        return None

    cleaned = raw.strip()
    if cleaned == "":
        return None

    if cleaned.lower().startswith("x"):
        cleaned = cleaned.split("=", 1)[-1].strip() if "=" in cleaned else cleaned

    try:
        expr = parse_expr(cleaned)
        simplified = sp.nsimplify(expr)

        # Reject anything that isn't a pure number — e.g. "banana" parses
        # as a symbol, not a number, and shouldn't count as a real answer.
        if not simplified.is_number:
            return None

        return simplified
    except Exception:
        return None


def _classify_mistake(parsed, canonical) -> str:
    """
    Crude first-pass mistake classification.
    Extend this over time as we see more real mistake patterns.
    """
    # Sign error: user got the right magnitude but wrong sign
    if parsed == -canonical:
        return "sign_error"

    # Off-by-a-small-amount: could indicate an arithmetic slip rather than a conceptual one
    try:
        diff = abs(parsed - canonical)
        if diff != 0 and diff <= 2:
            return "arithmetic_slip"
    except TypeError:
        pass  # parsed/canonical aren't directly comparable numerically

    return "wrong"