import sympy as sp
from sympy import symbols
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)

from schemas import AnswerShape

x = symbols('x')

# Allow implicit multiplication so "2x" parses, but we still reject symbolic answers
TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)


def verify_answer(problem: dict, user_answer: str) -> dict:
    """
    Verifies a user's answer against a problem's canonical_answer.
    Dispatches to a shape-specific checker based on problem["answer_shape"] —
    see SHAPE_CHECKERS at the bottom of this file.

    Returns (shape of the dict is the same across all checkers):
        {
            "correct": bool,
            "parsed_answer": shape-dependent (sympy number, set, etc.) or None,
            "mistake_type": str or None,
            "not_serious": bool   ← True if input was invalid OR a sneaky expression
        }
    """
    shape = problem["answer_shape"]
    checker = SHAPE_CHECKERS.get(shape)
    if checker is None:
        raise ValueError(f"No verifier implemented for answer shape: {shape}")
    return checker(problem, user_answer)


# ─────────────────────────────────────────────────────────────────────────────
# single_value — e.g. linear equations, definite integrals, determinants
# ─────────────────────────────────────────────────────────────────────────────

def _verify_single_value(problem: dict, user_answer: str) -> dict:
    """
    mistake_type values:
        None              — correct
        "sign_error"      — right magnitude, wrong sign
        "arithmetic_slip" — off by <= 2
        "wrong"           — everything else
    """
    canonical = problem["canonical_answer"]
    parsed, is_expression = _parse_user_answer(user_answer, canonical)

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
            "mistake_type": None if is_correct else _classify_single_mistake(parsed, canonical),
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
        "mistake_type": _classify_single_mistake(parsed, canonical),
        "not_serious": False,
    }


def _classify_single_mistake(parsed, canonical) -> str:
    if parsed == -canonical:
        return "sign_error"
    try:
        diff = abs(parsed - canonical)
        if diff != 0 and diff <= 2:
            return "arithmetic_slip"
    except TypeError:
        pass
    return "wrong"


# ─────────────────────────────────────────────────────────────────────────────
# multi_value — e.g. quadratic roots, trig solve-on-interval
#
# canonical_answer for these problems must be a set (or any iterable) of
# sympy numbers — the full set of valid answers.
# User submits a comma-separated list, e.g. "2, -3" or "x = 2, 3".
# ─────────────────────────────────────────────────────────────────────────────

def _verify_multi_value(problem: dict, user_answer: str) -> dict:
    """
    mistake_type values:
        None       — correct (exact set match)
        "partial"  — at least one submitted value is correct, but the full
                      set doesn't match (missing values, extra wrong values,
                      or both)
        "wrong"    — no submitted value is correct
    """
    canonical = set(problem["canonical_answer"])
    parsed, is_expression = _parse_multi_value_answer(user_answer, canonical)

    if parsed is None:
        return {
            "correct": False,
            "parsed_answer": None,
            "mistake_type": None,
            "not_serious": True,
        }

    is_correct = (parsed == canonical)

    if is_expression:
        return {
            "correct": is_correct,
            "parsed_answer": parsed,
            "mistake_type": None if is_correct else _classify_multi_mistake(parsed, canonical),
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
        "mistake_type": _classify_multi_mistake(parsed, canonical),
        "not_serious": False,
    }


def _classify_multi_mistake(parsed: set, canonical: set) -> str:
    if parsed & canonical:  # any overlap at all with the correct set
        return "partial"
    return "wrong"


def _parse_multi_value_answer(raw: str, canonical=None):
    """
    Parses a comma-separated list of numeric tokens.
    Returns (set_of_values, any_expression) or (None, False) if the input is
    empty, or if ANY token fails to parse as a number — one bad token
    invalidates the whole answer rather than silently dropping it.

    canonical (the correct set) determines whether compound-looking tokens
    count as "lazy" — see _expects_integer_form.
    """
    if raw is None:
        return None, False

    cleaned = raw.strip()
    if not cleaned:
        return None, False

    if cleaned.lower().startswith("x") and "=" in cleaned:
        cleaned = cleaned.split("=", 1)[-1].strip()

    tokens = [t.strip() for t in cleaned.split(",") if t.strip()]
    if not tokens:
        return None, False

    strict = _expects_integer_form(canonical)

    values = set()
    any_expression = False
    for token in tokens:
        value, is_expr = _parse_number_token(token, strict=strict)
        if value is None:
            return None, False
        values.add(value)
        any_expression = any_expression or is_expr

    return values, any_expression


# ─────────────────────────────────────────────────────────────────────────────
# vector_or_matrix — e.g. vectors, matrix results (determinant itself is
# single_value; this is for results that are matrices/tuples, not scalars)
# NOT IMPLEMENTED YET — no topic uses this shape yet. Planned for
# matrices & determinants, linear algebra systems, 3D geometry & vectors.
# Deliberately left unimplemented rather than guessed at, since designing
# the checker without a real generator to test against risks getting the
# comparison semantics (element-wise tolerance? exact? up to scalar multiple
# for direction vectors?) wrong and having to redo it.
# ─────────────────────────────────────────────────────────────────────────────

def _verify_vector_or_matrix(problem: dict, user_answer: str) -> dict:
    raise NotImplementedError(
        "vector_or_matrix verification isn't implemented yet — no topic uses "
        "this answer shape yet."
    )


# ─────────────────────────────────────────────────────────────────────────────
# expression — e.g. equation of a line/circle/conic, indefinite integrals,
# differential equations. Checked by SymPy equivalence (e.g. differentiate
# the user's indefinite-integral answer and compare to the integrand, or
# check proportional coefficients for a line/circle), never string match.
# NOT IMPLEMENTED YET — no topic uses this shape yet.
# ─────────────────────────────────────────────────────────────────────────────

def _verify_expression(problem: dict, user_answer: str) -> dict:
    raise NotImplementedError(
        "expression verification isn't implemented yet — no topic uses this "
        "answer shape yet."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared parsing helpers (single_value and multi_value both use these)
# ─────────────────────────────────────────────────────────────────────────────

def _parse_user_answer(raw: str, canonical=None):
    """
    Returns (parsed_value, is_expression) for a SINGLE numeric answer.
    - parsed_value: sympy number, or None if unparseable
    - is_expression: True if the input was a compound expression (e.g. "11-2")
      rather than a plain number literal (e.g. "9" or "-9" or "009")

    canonical (the correct answer) determines whether compound-looking tokens
    count as "lazy" — see _expects_integer_form.
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

    strict = _expects_integer_form(canonical)
    return _parse_number_token(cleaned, strict=strict)


def _expects_integer_form(canonical) -> bool:
    """
    True if the canonical answer is a plain integer, meaning any compound
    input from the student (a fraction, a pi-multiple, an arithmetic
    expression) represents UNREDUCED arithmetic rather than a legitimate
    closed form — e.g. typing "18/2" instead of "9" for a linear equation.

    False for fractional (probability, statistics), or pi-based
    (trigonometry) canonical answers, where forms like "3/8" or "5*pi/6" ARE
    the correct final answer, not laziness — flagging those as "not_serious"
    would tell a student who answered correctly that they're being cheeky.

    Defaults to True (the stricter/original behavior) if canonical isn't a
    recognizable number or set of numbers.
    """
    try:
        if isinstance(canonical, (set, frozenset, list, tuple)):
            return all(_expects_integer_form(v) for v in canonical)
        return bool(canonical.is_Integer)
    except AttributeError:
        return True


def _parse_number_token(cleaned: str, strict: bool = True):
    """
    Core numeric-token parser — shared by _parse_user_answer (single_value)
    and _parse_multi_value_answer (multi_value). Takes an already-cleaned
    string (no surrounding whitespace, no "x=" prefix) and returns
    (value, is_expression) or (None, False) on failure.

    Plain number detection: strip the optional leading minus, strip leading
    zeros, strip whitespace — if what remains is purely digits (and
    optionally one decimal point), it's a plain number. "009" -> plain.
    "11-2" -> expression. "3.0" -> plain.

    strict=False (canonical answer isn't a plain integer) skips the
    "is_expression" flag entirely — compound-looking input like "3/8" or
    "5*pi/6" is treated as a normal, non-lazy answer rather than a sneaky
    expression, since it may well be the correct closed form.
    """
    if not cleaned:
        return None, False

    is_plain_number = _looks_like_plain_number(cleaned)

    # Normalise plain numbers before parsing — strip leading zeros from the
    # numeric part so "-05" -> "-5" and "009" -> "9".
    # SymPy's parser can treat zero-padded literals as octal and reject them.
    if is_plain_number:
        cleaned = _strip_leading_zeros(cleaned)

    try:
        expr = parse_expr(cleaned, transformations=TRANSFORMATIONS)
        simplified = sp.nsimplify(expr, rational=True)

        # Reject anything that isn't a pure number (e.g. bare variable names)
        if not simplified.is_number:
            return None, False

        is_expression = (not is_plain_number) and strict
        return simplified, is_expression

    except Exception:
        return None, False


def _strip_leading_zeros(s: str) -> str:
    """
    Strips leading zeros from a plain number string, preserving sign and decimals.
    "-05"  -> "-5"
    "009"  -> "9"
    "00.5" -> "0.5"   (keeps one zero before the dot)
    "-007" -> "-7"
    "0"    -> "0"
    """
    negative = s.startswith("-")
    magnitude = s.lstrip("-")

    if "." in magnitude:
        integer_part, decimal_part = magnitude.split(".", 1)
        integer_part = integer_part.lstrip("0") or "0"
        magnitude = f"{integer_part}.{decimal_part}"
    else:
        magnitude = magnitude.lstrip("0") or "0"

    return f"-{magnitude}" if negative else magnitude


def _looks_like_plain_number(s: str) -> bool:
    """
    Returns True for things like: "9", "-9", "009", "3.0", "-007", "9.0"
    Returns False for: "11-2", "3+6", "18/2", "2*4"
    """
    candidate = s.lstrip("-").strip()
    parts = candidate.split(".")
    if len(parts) > 2:
        return False
    return all(part.isdigit() for part in parts if part)


# ─────────────────────────────────────────────────────────────────────────────
# Shape -> checker registry. To add a shape's verification: write a
# _verify_<shape>(problem, user_answer) function above and register it here.
# ─────────────────────────────────────────────────────────────────────────────

SHAPE_CHECKERS = {
    AnswerShape.SINGLE_VALUE: _verify_single_value,
    AnswerShape.MULTI_VALUE: _verify_multi_value,
    AnswerShape.VECTOR_OR_MATRIX: _verify_vector_or_matrix,
    AnswerShape.EXPRESSION: _verify_expression,
}
