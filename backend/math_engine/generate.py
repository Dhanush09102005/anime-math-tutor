import random
import sympy as sp
from sympy import symbols, Eq, solve

x = symbols('x')

def generate_problem(topic: str, difficulty: int) -> dict:
    """
    Generates a math problem for the given topic and difficulty.
    difficulty: 1 (easiest) to 5+ (hardest) — controls coefficient size/complexity.

    Returns a dict:
        {
            "id": str,
            "topic": str,
            "difficulty": int,
            "prompt_text": str,          # shown to the user
            "equation": sympy Eq,        # the actual equation object
            "canonical_answer": sympy expr  # ground truth, used by verify_answer
        }
    """
    if topic == "linear_equations":
        return _generate_linear_equation(difficulty)
    else:
        raise ValueError(f"Unknown topic: {topic}")


def _generate_linear_equation(difficulty: int) -> dict:
    # Difficulty controls the range coefficients are pulled from.
    # Low difficulty = small, friendly numbers. Higher = bigger, messier ones.
    coeff_range = 5 + (difficulty * 3)   # e.g. difficulty 1 -> range 8, difficulty 5 -> range 20
    const_range = 10 + (difficulty * 5)

    # Pick a random non-zero coefficient for x
    a = random.choice([n for n in range(-coeff_range, coeff_range + 1) if n != 0])
    b = random.randint(-const_range, const_range)

    # Pick a "nice" integer answer first, then derive c backwards.
    # This guarantees the answer is always a clean integer, not a fraction —
    # important for difficulty 1-2 so early problems aren't accidentally hard.
    answer = random.randint(-10, 10)
    c = a * answer + b

    equation = Eq(a * x + b, c)
    canonical_answer = solve(equation, x)[0]  # sympy returns a list; take the single solution

    prompt_text = f"Solve for x: {a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}"

    return {
        "id": f"linear_{random.randint(1000,9999)}",
        "topic": "linear_equations",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "equation": equation,
        "canonical_answer": canonical_answer,
    }