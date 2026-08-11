import sympy as sp
from sympy import symbols
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

x = symbols('x')

# Allow implicit multiplication so "2x" parses, but we still reject symbolic answers
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def verify_answer(problem: dict, user_answer: str) -> dict:
    """
    Verifies a user's answer against a problem's canonical_answer.

    Returns:
        {
            "correct": bool,
            "parsed_answer": sympy expr or None,
            "mistake_type": str or None,
            "not_serious": bool   ← True if input was invalid OR a sneaky expression
        }

    mistake_type values:
        None            — correct
        "sign_error"    — right magnitude, wrong sign
        "arithmetic_slip" — off by ≤ 2
        "wrong"         — everything else
        (not_serious answers always have correct=False or correct=True with not_serious=True)
    """
    canonical = problem["canonical_answer"]
    parsed, is_expression = _parse_user_answer(user_answer)

    # Could not parse at all — garbage input
    if parsed is None:
        return {
            "correct": False,
            "parsed_answer": None,
            "mistake_type": None,
            "not_serious": True,
        }

    is_correct = (parsed == canonical)

    # Input was a compound expression like "11-2" instead of just "9"
    # Mark not_serious regardless of whether the value is right
    if is_expression:
        return {
            "correct": is_correct,
            "parsed_answer": parsed,
            "mistake_type": None if is_correct else _classify_mistake(parsed, canonical),
            "not_serious": True,
        }

    if is_correct:
        return {
            "correct": True,
            "parsed_answer": parsed,
            "mistake_type": None,
            "not_serious": False,
        }

    return {
        "correct": False,
        "parsed_answer": parsed,
        "mistake_type": _classify_mistake(parsed, canonical),
        "not_serious": False,
    }


def _parse_user_answer(raw: str):
    """
    Returns (parsed_value, is_expression).
    - parsed_value: sympy number, or None if unparseable
    - is_expression: True if the input was a compound expression (e.g. "11-2")
      rather than a plain number literal (e.g. "9" or "-9" or "009")

    Plain number detection:
    Strip the optional leading minus, strip leading zeros, strip whitespace —
    if what remains is purely digits (and optionally one decimal point), it's
    a plain number. "009" → plain. "11-2" → expression. "3.0" → plain.
    """
    if raw is None:
        return None, False

    cleaned = raw.strip()
    if not cleaned:
        return None, False

    # Strip x= prefix ("x = 5" or "x=5")
    if cleaned.lower().startswith("x"):
        cleaned = cleaned.split("=", 1)[-1].strip() if "=" in cleaned else cleaned.lstrip("xX =")

    if not cleaned:
        return None, False

    # Determine if this looks like a plain number literal vs an expression
    is_plain_number = _looks_like_plain_number(cleaned)

    try:
        expr = parse_expr(cleaned, transformations=TRANSFORMATIONS)
        simplified = sp.nsimplify(expr, rational=True)

        # Reject anything that isn't a pure number (e.g. bare variable names)
        if not simplified.is_number:
            return None, False

        return simplified, not is_plain_number

    except Exception:
        return None, False


def _looks_like_plain_number(s: str) -> bool:
    """
    Returns True for things like: "9", "-9", "009", "3.0", "-007", "9.0"
    Returns False for: "11-2", "3+6", "18/2", "2*4"
    """
    candidate = s.lstrip("-").strip()
    # After stripping a leading minus, should be only digits + at most one dot
    parts = candidate.split(".")
    if len(parts) > 2:
        return False
    return all(part.isdigit() for part in parts if part)


def _classify_mistake(parsed, canonical) -> str:
    if parsed == -canonical:
        return "sign_error"
    try:
        diff = abs(parsed - canonical)
        if diff != 0 and diff <= 2:
            return "arithmetic_slip"
    except TypeError:
        pass
    return "wrong"
