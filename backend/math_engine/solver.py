"""
Teaching mode solver — takes a plain-text math problem (extracted from user input),
attempts to parse and solve it with SymPy, and returns a structured result that
the character can use to explain the solution.

Design: the LLM extracted the problem text. SymPy solves it.
The character narrates toward SymPy's answer — not its own.
This preserves the no-LLM-grading principle in teaching mode.
"""

import re
import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
)
from sympy import symbols, Eq, solve, simplify, diff, integrate, limit, Symbol

TRANSFORMATIONS = standard_transformations + (implicit_multiplication_application,)

x, y, z, n, t = symbols("x y z n t")


def solve_problem(problem_text: str) -> dict:
    """
    Attempts to solve a math problem given as plain text.

    Returns:
    {
        "solved": bool,
        "problem_text": str,        # cleaned input
        "solution": str,            # human-readable answer
        "steps": list[str],         # intermediate steps for the character to narrate
        "error": str | None         # if solved=False, why it failed
    }
    """
    cleaned = problem_text.strip()

    # Try each solver in order — first match wins
    for solver_fn in [
        _try_linear_equation,
        _try_quadratic_equation,
        _try_general_equation,
        _try_derivative,
        _try_definite_integral,
        _try_expression_simplify,
    ]:
        result = solver_fn(cleaned)
        if result is not None:
            return {**result, "problem_text": cleaned, "error": None, "solved": True}

    return {
        "solved": False,
        "problem_text": cleaned,
        "solution": None,
        "steps": [],
        "error": (
            "I couldn't parse this into something SymPy can solve directly. "
            "The character will explain based on the problem text alone."
        ),
    }


def _try_linear_equation(text: str) -> dict | None:
    """Handles: solve for x, 3x + 2 = 11 style problems."""
    eq_match = re.search(r"(.+?)\s*=\s*(.+)", text)
    if not eq_match:
        return None

    try:
        lhs = parse_expr(eq_match.group(1), transformations=TRANSFORMATIONS)
        rhs = parse_expr(eq_match.group(2), transformations=TRANSFORMATIONS)
        equation = Eq(lhs, rhs)

        # Find which symbol to solve for
        free = equation.free_symbols
        if not free:
            return None
        target = sorted(free, key=lambda s: s.name)[0]  # alphabetical, so x before y

        solutions = solve(equation, target)
        if not solutions:
            return None

        sol_str = ", ".join(str(sp.nsimplify(s, rational=True)) for s in solutions)
        return {
            "solution": f"{target} = {sol_str}",
            "steps": [
                f"Equation: {equation}",
                f"Solving for {target}",
                f"Solution: {target} = {sol_str}",
            ],
        }
    except Exception:
        return None


def _try_quadratic_equation(text: str) -> dict | None:
    """Handles quadratic equations — same path as linear but keeps both roots."""
    return _try_linear_equation(text)  # solve() already returns both roots


def _try_general_equation(text: str) -> dict | None:
    """Last-resort equation solver — tries to parse and solve anything with an '='."""
    return _try_linear_equation(text)


def _try_derivative(text: str) -> dict | None:
    """Handles: find d/dx, derivative of f(x) style problems."""
    deriv_match = re.search(
        r"(?:derivative|differentiate|d/d[xyz]|find\s+f')\s*(?:of\s+)?(.+)",
        text, re.IGNORECASE
    )
    if not deriv_match:
        return None
    try:
        expr_str = deriv_match.group(1).strip().rstrip(".")
        expr = parse_expr(expr_str, transformations=TRANSFORMATIONS)
        result = diff(expr, x)
        simplified = simplify(result)
        return {
            "solution": str(simplified),
            "steps": [
                f"Expression: {expr}",
                f"d/dx = {result}",
                f"Simplified: {simplified}",
            ],
        }
    except Exception:
        return None


def _try_definite_integral(text: str) -> dict | None:
    """Handles: integrate f(x) from a to b style problems."""
    int_match = re.search(
        r"(?:integrate|integral|∫)\s+(.+?)\s+(?:from|between)\s+([\d\-\.]+)\s+(?:to|and)\s+([\d\-\.]+)",
        text, re.IGNORECASE
    )
    if not int_match:
        return None
    try:
        expr = parse_expr(int_match.group(1).strip(), transformations=TRANSFORMATIONS)
        a = float(int_match.group(2))
        b = float(int_match.group(3))
        result = integrate(expr, (x, a, b))
        simplified = sp.nsimplify(result, rational=True)
        return {
            "solution": str(simplified),
            "steps": [
                f"Integrand: {expr}",
                f"Limits: {a} to {b}",
                f"∫ = {result} = {simplified}",
            ],
        }
    except Exception:
        return None


def _try_expression_simplify(text: str) -> dict | None:
    """Last resort — try to parse and simplify as a bare expression."""
    try:
        expr = parse_expr(text, transformations=TRANSFORMATIONS)
        simplified = simplify(expr)
        if simplified == expr:
            return None  # nothing useful happened
        return {
            "solution": str(simplified),
            "steps": [
                f"Expression: {expr}",
                f"Simplified: {simplified}",
            ],
        }
    except Exception:
        return None
