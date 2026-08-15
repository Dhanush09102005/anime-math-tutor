import random
import sympy as sp
from sympy import symbols, Eq, solve, Rational, binomial, Matrix, diff, integrate, limit, pi, sqrt

from schemas import AnswerShape

x = symbols('x')

def generate_problem(topic: str, difficulty: int) -> dict:
    """
    Generates a math problem for the given topic and difficulty.
    difficulty: 1 (easiest) to 5+ (hardest) — controls coefficient size/complexity.

    Dispatches to a per-topic generator via TOPIC_GENERATORS (defined at the
    bottom of this file). Each generator returns a dict:
        {
            "id": str,
            "topic": str,
            "difficulty": int,
            "prompt_text": str,             # shown to the user
            "answer_shape": AnswerShape,    # tells verify_answer which checker to use
            "canonical_answer": ...,        # ground truth — shape/type depends on answer_shape
            ...                              # topic-specific fields the verifier needs
                                              # (e.g. "equation" for linear_equations)
        }

    To add a new topic: write a _generate_<topic>(difficulty) function, tag
    its return dict with the correct AnswerShape, and register it in
    TOPIC_GENERATORS below.

    DESIGN NOTE (v1.2.0): every generator below is deliberately phrased so its
    answer is a single_value or multi_value — e.g. "find the determinant"
    (a number) rather than "find the resulting matrix". This lets every JEE
    topic go live now on the two answer shapes that are actually implemented
    and tested. vector_or_matrix and expression-shaped questions (equation of
    a line, a raw matrix result, indefinite integrals) are a deliberately
    separate later pass — see verify.py's NotImplementedError stubs.
    """
    generator = TOPIC_GENERATORS.get(topic)
    if generator is None:
        raise ValueError(f"Unknown topic: {topic}")
    return generator(difficulty)


def _rand_id(prefix: str) -> str:
    return f"{prefix}_{random.randint(1000,9999)}"


def _signed(n) -> str:
    """Formats a coefficient's sign+magnitude for 'A + 5' / 'A - 5' style prompts."""
    return f"+ {n}" if n >= 0 else f"- {abs(n)}"


# ─────────────────────────────────────────────────────────────────────────────
# Foundations
# ─────────────────────────────────────────────────────────────────────────────

def _generate_linear_equation(difficulty: int) -> dict:
    coeff_range = 5 + (difficulty * 3)
    const_range = 10 + (difficulty * 5)

    a = random.choice([n for n in range(-coeff_range, coeff_range + 1) if n != 0])
    b = random.randint(-const_range, const_range)

    answer = random.randint(-10, 10)
    c = a * answer + b

    equation = Eq(a * x + b, c)
    canonical_answer = solve(equation, x)[0]

    prompt_text = f"Solve for x: {a}x {'+' if b >= 0 else '-'} {abs(b)} = {c}"

    return {
        "id": _rand_id("linear"),
        "topic": "linear_equations",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "equation": equation,
        "canonical_answer": canonical_answer,
    }


def _generate_numbers(difficulty: int) -> dict:
    """Remainder problems — 'playing with numbers'. Always a clean non-negative integer."""
    divisor = random.randint(3 + difficulty, 9 + difficulty * 2)
    quotient = random.randint(2, 5 + difficulty)
    remainder = random.randint(1, divisor - 1)
    dividend = divisor * quotient + remainder

    prompt_text = f"What is the remainder when {dividend} is divided by {divisor}?"

    return {
        "id": _rand_id("numbers"),
        "topic": "numbers",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(remainder),
    }


def _generate_logarithms(difficulty: int) -> dict:
    """log_b(value) where value = b**exponent — guarantees a clean integer answer."""
    base = random.choice([2, 3, 5] if difficulty < 4 else [2, 3, 5, 7])
    exponent = random.randint(1, 3 + difficulty // 2)
    value = base ** exponent

    prompt_text = f"Evaluate: log base {base} of {value}"

    return {
        "id": _rand_id("log"),
        "topic": "logarithms",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(exponent),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Algebra
# ─────────────────────────────────────────────────────────────────────────────

def _generate_quadratic_equation(difficulty: int) -> dict:
    """Picks two distinct integer roots first, expands backwards — always clean roots."""
    root_range = 5 + difficulty * 2
    r1 = random.randint(-root_range, root_range)
    r2 = random.choice([n for n in range(-root_range, root_range + 1) if n != r1])

    leading = random.choice([1, 1, 1, 2]) if difficulty >= 4 else 1  # non-1 leading coeff at higher difficulty

    b = -leading * (r1 + r2)
    c = leading * r1 * r2

    lead_str = "" if leading == 1 else str(leading)
    prompt_text = f"Solve for x: {lead_str}x^2 {_signed(b)}x {_signed(c)} = 0"

    return {
        "id": _rand_id("quad"),
        "topic": "quadratic_equations",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.MULTI_VALUE,
        "canonical_answer": [sp.Integer(r1), sp.Integer(r2)],
    }


def _generate_progressions(difficulty: int) -> dict:
    """nth term of an arithmetic progression."""
    a = random.randint(-10 - difficulty, 10 + difficulty)
    d = random.choice([n for n in range(-5 - difficulty, 6 + difficulty) if n != 0])
    n = random.randint(4, 10 + difficulty)

    nth_term = a + (n - 1) * d

    prompt_text = (
        f"An arithmetic progression has first term {a} and common difference {d}. "
        f"Find the {n}th term."
    )

    return {
        "id": _rand_id("prog"),
        "topic": "progressions",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(nth_term),
    }


def _generate_binomial_theorem(difficulty: int) -> dict:
    """Coefficient of x^k in (1+x)^n — i.e. C(n,k). Always a clean integer."""
    n = random.randint(4 + difficulty, 8 + difficulty)
    k = random.randint(1, n - 1)

    coeff = binomial(n, k)

    prompt_text = f"Find the coefficient of x^{k} in the expansion of (1 + x)^{n}."

    return {
        "id": _rand_id("binom"),
        "topic": "binomial_theorem",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(coeff),
    }


def _generate_complex_numbers(difficulty: int) -> dict:
    """
    Modulus of a complex number a + bi. Deliberately asks for the modulus
    (a real number) rather than requiring the student to type a complex
    number back — sidesteps parsing "i" vs "I" entirely, and keeps this on
    the single_value shape.
    """
    triples = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (7, 24, 25), (9, 12, 15)]
    a, b, mag = random.choice(triples[: 2 + difficulty] if difficulty < len(triples) else triples)
    if random.random() < 0.5:
        a, b = b, a
    sign_b = "+" if random.random() < 0.5 else "-"

    prompt_text = f"Find |z| for z = {a} {sign_b} {b}i"

    return {
        "id": _rand_id("complex"),
        "topic": "complex_numbers",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(mag),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Trigonometry — curated exact solutions, not solved symbolically at runtime,
# so correctness is guaranteed by construction rather than by trusting solve().
# ─────────────────────────────────────────────────────────────────────────────

_TRIG_TABLE = [
    ("sin(x) = 1/2",           [pi/6, 5*pi/6]),
    ("sin(x) = -1/2",          [7*pi/6, 11*pi/6]),
    ("cos(x) = 1/2",           [pi/3, 5*pi/3]),
    ("cos(x) = -1/2",          [2*pi/3, 4*pi/3]),
    ("sin(x) = sqrt(2)/2",     [pi/4, 3*pi/4]),
    ("cos(x) = sqrt(2)/2",     [pi/4, 7*pi/4]),
    ("sin(x) = sqrt(3)/2",     [pi/3, 2*pi/3]),
    ("cos(x) = sqrt(3)/2",     [pi/6, 11*pi/6]),
    ("tan(x) = 1",             [pi/4, 5*pi/4]),
    ("tan(x) = -1",            [3*pi/4, 7*pi/4]),
    ("tan(x) = sqrt(3)",       [pi/3, 4*pi/3]),
]


def _generate_trigonometry(difficulty: int) -> dict:
    pool_size = min(len(_TRIG_TABLE), 4 + difficulty)
    equation_str, solutions = random.choice(_TRIG_TABLE[:pool_size])

    prompt_text = f"Solve for x in [0, 2*pi): {equation_str}"

    return {
        "id": _rand_id("trig"),
        "topic": "trigonometry",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.MULTI_VALUE,
        "canonical_answer": list(solutions),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Probability & Statistics
# ─────────────────────────────────────────────────────────────────────────────

def _generate_probability(difficulty: int) -> dict:
    """P(drawing a specific color) from a bag — canonical answer is a Rational fraction."""
    red = random.randint(2, 5 + difficulty)
    blue = random.randint(2, 5 + difficulty)

    prob = Rational(red, red + blue)

    prompt_text = (
        f"A bag contains {red} red balls and {blue} blue balls. "
        "One ball is drawn at random. What is the probability it is red? "
        "(Answer as a fraction, e.g. 3/8)"
    )

    return {
        "id": _rand_id("prob"),
        "topic": "probability",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": prob,
    }


def _generate_statistics(difficulty: int) -> dict:
    """Mean of a small list of integers — canonical answer may be a fraction."""
    count = random.randint(4, 6 + difficulty // 2)
    values = [random.randint(-10 - difficulty, 10 + difficulty) for _ in range(count)]

    mean = Rational(sum(values), count)

    prompt_text = f"Find the mean of: {', '.join(str(v) for v in values)}"

    return {
        "id": _rand_id("stats"),
        "topic": "statistics",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": mean,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Coordinate Geometry — distance between two points, built from Pythagorean
# triples so the answer is always a clean integer.
# ─────────────────────────────────────────────────────────────────────────────

_PYTHAGOREAN_TRIPLES = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (7, 24, 25), (20, 21, 29)]


def _generate_coordinate_geometry(difficulty: int) -> dict:
    pool = _PYTHAGOREAN_TRIPLES[: 2 + difficulty] if difficulty < len(_PYTHAGOREAN_TRIPLES) else _PYTHAGOREAN_TRIPLES
    dx, dy, dist = random.choice(pool)
    if random.random() < 0.5:
        dx, dy = dy, dx

    x1, y1 = random.randint(-10, 10), random.randint(-10, 10)
    x2, y2 = x1 + dx * random.choice([1, -1]), y1 + dy * random.choice([1, -1])

    prompt_text = f"Find the distance between the points ({x1}, {y1}) and ({x2}, {y2})."

    return {
        "id": _rand_id("coordgeo"),
        "topic": "coordinate_geometry",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(dist),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Calculus — limits, derivative-at-a-point, definite integrals of polynomials
# only. Restricting to polynomials keeps every SymPy call (diff/integrate/
# limit) reliable and closed-form — no risk of indeterminate forms or
# integration failures.
# ─────────────────────────────────────────────────────────────────────────────

def _format_polynomial(expr) -> str:
    """
    Renders a sympy polynomial in the app's math-notation style ('6x - 23',
    'x^2') instead of Python repr ('6*x - 23', 'x**2').
    """
    return str(expr).replace("**", "^").replace("*", "")


def _random_polynomial(difficulty: int):
    degree = random.randint(2, min(4, 2 + difficulty // 3))
    coeffs = [random.randint(-5 - difficulty, 5 + difficulty) for _ in range(degree + 1)]
    if coeffs[0] == 0:
        coeffs[0] = random.choice([1, -1, 2, -2])
    expr = sum(c * x**i for i, c in enumerate(reversed(coeffs)))
    return expr


def _generate_calculus(difficulty: int) -> dict:
    kind = random.choice(["derivative", "definite_integral", "limit"])
    expr = _random_polynomial(difficulty)

    if kind == "derivative":
        point = random.randint(-3, 3)
        deriv = diff(expr, x)
        answer = deriv.subs(x, point)
        prompt_text = f"If f(x) = {_format_polynomial(expr)}, find f'({point})."

    elif kind == "definite_integral":
        a, b = sorted(random.sample(range(-4, 5), 2))
        answer = integrate(expr, (x, a, b))
        prompt_text = f"Evaluate the definite integral of {_format_polynomial(expr)} dx from x = {a} to x = {b}."

    else:  # limit — polynomials are continuous everywhere, so this is just substitution
        point = random.randint(-3, 3)
        answer = limit(expr, x, point)
        prompt_text = f"Find the limit as x approaches {point} of {_format_polynomial(expr)}."

    answer = sp.nsimplify(answer, rational=True)

    return {
        "id": _rand_id("calc"),
        "topic": "calculus",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": answer,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Linear Algebra — eigenvalues of a 2x2 integer matrix (multi_value).
#
# Construction: pick eigenvalues lambda1, lambda2 directly, build via
# M = P * diag(lambda1, lambda2) * P^-1 where P is a fixed unimodular
# (det = +/-1) integer matrix — this guarantees P^-1 is also integer, so M
# comes out as a clean integer matrix with EXACTLY those eigenvalues, by
# construction (not solved for after the fact).
# ─────────────────────────────────────────────────────────────────────────────

_UNIMODULAR_P = [Matrix([[1, 1], [1, 2]]), Matrix([[2, 1], [1, 1]]), Matrix([[1, 2], [1, 3]])]


def _generate_linear_algebra(difficulty: int) -> dict:
    eig_range = 4 + difficulty
    l1 = random.randint(-eig_range, eig_range)
    l2 = random.choice([n for n in range(-eig_range, eig_range + 1) if n != l1])

    P = random.choice(_UNIMODULAR_P)
    D = Matrix([[l1, 0], [0, l2]])
    M = P * D * P.inv()
    M = M.applyfunc(lambda v: sp.nsimplify(v, rational=True))

    rows = M.tolist()
    matrix_str = "[[{}, {}], [{}, {}]]".format(rows[0][0], rows[0][1], rows[1][0], rows[1][1])
    prompt_text = f"Find the eigenvalues of the matrix {matrix_str}."

    return {
        "id": _rand_id("linalg"),
        "topic": "linear_algebra",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.MULTI_VALUE,
        "canonical_answer": [sp.Integer(l1), sp.Integer(l2)],
    }


def _generate_matrices_determinants(difficulty: int) -> dict:
    """Determinant of a 2x2 (or 3x3 at higher difficulty) integer matrix."""
    size = 3 if difficulty >= 6 else 2
    coeff_range = 4 + difficulty // 2
    M = Matrix([[random.randint(-coeff_range, coeff_range) for _ in range(size)] for _ in range(size)])
    det = M.det()

    rows = M.tolist()
    matrix_str = str(rows).replace("], [", "], [")
    prompt_text = f"Find the determinant of the matrix {matrix_str}."

    return {
        "id": _rand_id("matdet"),
        "topic": "matrices_determinants",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(det),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3D Geometry & Vectors — dot product of two integer vectors. Chosen over
# magnitude specifically to avoid sqrt-of-non-perfect-square answers without
# needing a lookup table — dot product of integer vectors is always an
# integer, no construction tricks needed.
# ─────────────────────────────────────────────────────────────────────────────

def _generate_vectors_3d(difficulty: int) -> dict:
    comp_range = 4 + difficulty
    v1 = [random.randint(-comp_range, comp_range) for _ in range(3)]
    v2 = [random.randint(-comp_range, comp_range) for _ in range(3)]

    dot = sum(a * b for a, b in zip(v1, v2))

    prompt_text = f"Find the dot product of vectors a = {tuple(v1)} and b = {tuple(v2)}."

    return {
        "id": _rand_id("vec3d"),
        "topic": "vectors_3d",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(dot),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sets & Relations — inclusion-exclusion cardinality question. Keeps this on
# single_value (a count) rather than requiring true set-equality checking.
# ─────────────────────────────────────────────────────────────────────────────

def _generate_sets_relations(difficulty: int) -> dict:
    size_a = random.randint(5, 10 + difficulty)
    size_b = random.randint(5, 10 + difficulty)
    intersection = random.randint(1, min(size_a, size_b) - 1)

    union = size_a + size_b - intersection

    prompt_text = (
        f"Set A has {size_a} elements, Set B has {size_b} elements, and "
        f"|A intersect B| = {intersection}. Find |A union B|."
    )

    return {
        "id": _rand_id("sets"),
        "topic": "sets_relations",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": AnswerShape.SINGLE_VALUE,
        "canonical_answer": sp.Integer(union),
    }


# Topic registry — maps topic string to its generator function.
# This is the single place new topics get wired in.
TOPIC_GENERATORS = {
    "linear_equations": _generate_linear_equation,
    "numbers": _generate_numbers,
    "logarithms": _generate_logarithms,
    "quadratic_equations": _generate_quadratic_equation,
    "progressions": _generate_progressions,
    "binomial_theorem": _generate_binomial_theorem,
    "complex_numbers": _generate_complex_numbers,
    "trigonometry": _generate_trigonometry,
    "probability": _generate_probability,
    "statistics": _generate_statistics,
    "coordinate_geometry": _generate_coordinate_geometry,
    "calculus": _generate_calculus,
    "linear_algebra": _generate_linear_algebra,
    "matrices_determinants": _generate_matrices_determinants,
    "vectors_3d": _generate_vectors_3d,
    "sets_relations": _generate_sets_relations,
}
