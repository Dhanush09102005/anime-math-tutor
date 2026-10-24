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

    Generators may use any answer shape declared in schemas.py. Canonical
    answers are computed by SymPy or by construction, never by the LLM.
    """
    generator = TOPIC_GENERATORS.get(topic)
    if generator is None:
        raise ValueError(f"Unknown topic: {topic}")
    return generator(difficulty)


HYBRID_PROPOSAL_INSTRUCTIONS = {
    "linear_equations": (
        'Return JSON with integer fields "a", "b", and "solution"; '
        'a must be nonzero, each value must be between -20 and 20.'
    ),
    "quadratic_equations": (
        'Return JSON with integer fields "root1", "root2", and "leading"; '
        'the roots must be distinct and each value must be between -20 and 20; '
        '"leading" must be 1, 2, or 3.'
    ),
    "probability": (
        'Return JSON with integer fields "red" and "blue"; '
        'each value must be between 1 and 50.'
    ),
    "statistics": (
        'Return JSON with an integer array field "values" containing 4 to 8 '
        'values, each between -50 and 50.'
    ),
    "numbers": (
        'Return JSON integer fields "divisor" (3-30), "quotient" (2-20), '
        'and "remainder" (1 through divisor-1).'
    ),
    "logarithms": (
        'Return JSON integer fields "base" (2-10) and "exponent" (1-8).'
    ),
    "progressions": (
        'Return JSON integer fields "first_term" (-50 to 50), '
        '"difference" (-20 to 20, nonzero), and "term_number" (2-50).'
    ),
    "binomial_theorem": (
        'Return JSON integer fields "n" (4-30) and "k" (1 through n-1).'
    ),
    "complex_numbers": (
        'Return JSON fields "triple_index" (integer 0-5), "swap" (boolean), '
        'and "imaginary_sign" ("plus" or "minus").'
    ),
    "trigonometry": (
        'Return JSON integer field "equation_index" (0-10).'
    ),
    "coordinate_geometry": (
        'Return JSON integer fields "triple_index" (0-5), "x1" and "y1" '
        '(-20 to 20), "x_sign" and "y_sign" (each -1 or 1).'
    ),
    "calculus": (
        'Return JSON fields "kind" (one of "derivative", "definite_integral", '
        '"limit", "indefinite_integral"), "coefficients" (3-5 integers from '
        '-15 to 15 in ascending powers of x, with a nonzero final coefficient), '
        '"point" (-5 to 5), and "lower"/"upper" (-5 to 5 with lower < upper).'
    ),
    "linear_algebra": (
        'Return JSON integer fields "eigenvalue1" and "eigenvalue2" (-20 to 20, '
        'distinct), and "basis_index" (0-2).'
    ),
    "matrices_determinants": (
        'Return JSON field "operation" ("add", "subtract", or "determinant"), '
        '"matrix_a" (a 2x2 array of integers from -10 to 10), and "matrix_b" '
        '(another 2x2 array in the same range; required for add/subtract).'
    ),
    "vectors_3d": (
        'Return JSON field "operation" ("dot" or "cross") and integer arrays '
        '"vector_a" and "vector_b", each of length 3 with values from -10 to 10.'
    ),
    "sets_relations": (
        'Return JSON integer fields "size_a" and "size_b" (2-50) and '
        '"intersection" (1 through min(size_a,size_b)-1).'
    ),
}


def generate_problem_from_proposal(topic: str, difficulty: int, proposal: dict) -> dict:
    """Validate an LLM-proposed structure and compute its answer with SymPy."""
    if not isinstance(proposal, dict):
        raise ValueError("The proposed parameters must be a JSON object.")

    if topic == "linear_equations":
        a = _proposal_int(proposal, "a", -20, 20)
        b = _proposal_int(proposal, "b", -20, 20)
        answer = _proposal_int(proposal, "solution", -20, 20)
        if a == 0:
            raise ValueError("The proposed linear equation must have a nonzero coefficient.")
        c = a * answer + b
        equation = Eq(a * x + b, c)
        canonical_answer = solve(equation, x)[0]
        return _hybrid_result(
            topic, difficulty, "hybrid_linear",
            f"Solve for x: {a}x {_signed(b)} = {c}",
            AnswerShape.SINGLE_VALUE, canonical_answer, equation=equation,
        )

    if topic == "quadratic_equations":
        root1 = _proposal_int(proposal, "root1", -20, 20)
        root2 = _proposal_int(proposal, "root2", -20, 20)
        leading = _proposal_int(proposal, "leading", 1, 3)
        if root1 == root2:
            raise ValueError("The proposed quadratic must have two distinct roots.")
        b = -leading * (root1 + root2)
        c = leading * root1 * root2
        canonical_answer = sorted(solve(leading * x**2 + b * x + c, x), key=sp.default_sort_key)
        return _hybrid_result(
            topic, difficulty, "hybrid_quadratic",
            f"Solve for x: {leading}x^2 {_signed(b)}x {_signed(c)} = 0",
            AnswerShape.MULTI_VALUE, canonical_answer,
        )

    if topic == "probability":
        red = _proposal_int(proposal, "red", 1, 50)
        blue = _proposal_int(proposal, "blue", 1, 50)
        return _hybrid_result(
            topic, difficulty, "hybrid_probability",
            (
                f"A bag contains {red} red balls and {blue} blue balls. "
                "One ball is drawn at random. What is the probability it is red? "
                "(Answer as a fraction, e.g. 3/8)"
            ),
            AnswerShape.SINGLE_VALUE, Rational(red, red + blue),
        )

    if topic == "statistics":
        values = proposal.get("values")
        if (
            not isinstance(values, list)
            or not 4 <= len(values) <= 8
            or any(type(value) is not int or not -50 <= value <= 50 for value in values)
        ):
            raise ValueError("The proposed statistics values must be 4–8 bounded integers.")
        return _hybrid_result(
            topic, difficulty, "hybrid_statistics",
            f"Find the mean of: {', '.join(str(value) for value in values)}",
            AnswerShape.SINGLE_VALUE, Rational(sum(values), len(values)),
        )

    if topic == "numbers":
        divisor = _proposal_int(proposal, "divisor", 3, 30)
        quotient = _proposal_int(proposal, "quotient", 2, 20)
        remainder = _proposal_int(proposal, "remainder", 1, divisor - 1)
        dividend = divisor * quotient + remainder
        return _hybrid_result(
            topic, difficulty, "hybrid_numbers",
            f"What is the remainder when {dividend} is divided by {divisor}?",
            AnswerShape.SINGLE_VALUE, sp.Integer(remainder),
        )

    if topic == "logarithms":
        base = _proposal_int(proposal, "base", 2, 10)
        exponent = _proposal_int(proposal, "exponent", 1, 8)
        return _hybrid_result(
            topic, difficulty, "hybrid_log",
            f"Evaluate: log base {base} of {base ** exponent}",
            AnswerShape.SINGLE_VALUE, sp.Integer(exponent),
        )

    if topic == "progressions":
        first = _proposal_int(proposal, "first_term", -50, 50)
        difference = _proposal_int(proposal, "difference", -20, 20)
        term_number = _proposal_int(proposal, "term_number", 2, 50)
        if difference == 0:
            raise ValueError("The proposed progression difference must be nonzero.")
        answer = first + (term_number - 1) * difference
        return _hybrid_result(
            topic, difficulty, "hybrid_progression",
            f"An arithmetic progression has first term {first} and common "
            f"difference {difference}. Find the {term_number}th term.",
            AnswerShape.SINGLE_VALUE, sp.Integer(answer),
        )

    if topic == "binomial_theorem":
        n = _proposal_int(proposal, "n", 4, 30)
        k = _proposal_int(proposal, "k", 1, n - 1)
        return _hybrid_result(
            topic, difficulty, "hybrid_binomial",
            f"Find the coefficient of x^{k} in the expansion of (1 + x)^{n}.",
            AnswerShape.SINGLE_VALUE, sp.Integer(binomial(n, k)),
        )

    if topic == "complex_numbers":
        triple_index = _proposal_int(proposal, "triple_index", 0, 5)
        swap = _proposal_bool(proposal, "swap")
        imaginary_sign = proposal.get("imaginary_sign")
        if imaginary_sign not in ("plus", "minus"):
            raise ValueError('The proposed imaginary_sign must be "plus" or "minus".')
        triples = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17), (7, 24, 25), (9, 12, 15)]
        real, imaginary, magnitude = triples[triple_index]
        if swap:
            real, imaginary = imaginary, real
        sign = "+" if imaginary_sign == "plus" else "-"
        return _hybrid_result(
            topic, difficulty, "hybrid_complex",
            f"Find |z| for z = {real} {sign} {imaginary}i",
            AnswerShape.SINGLE_VALUE, sp.Integer(magnitude),
        )

    if topic == "trigonometry":
        index = _proposal_int(proposal, "equation_index", 0, len(_TRIG_TABLE) - 1)
        equation, solutions = _TRIG_TABLE[index]
        return _hybrid_result(
            topic, difficulty, "hybrid_trig",
            f"Solve for x in [0, 2*pi): {equation}",
            AnswerShape.MULTI_VALUE, list(solutions),
        )

    if topic == "coordinate_geometry":
        triple_index = _proposal_int(proposal, "triple_index", 0, len(_PYTHAGOREAN_TRIPLES) - 1)
        x1 = _proposal_int(proposal, "x1", -20, 20)
        y1 = _proposal_int(proposal, "y1", -20, 20)
        x_sign = _proposal_choice(proposal, "x_sign", (-1, 1))
        y_sign = _proposal_choice(proposal, "y_sign", (-1, 1))
        dx, dy, distance = _PYTHAGOREAN_TRIPLES[triple_index]
        x2, y2 = x1 + x_sign * dx, y1 + y_sign * dy
        return _hybrid_result(
            topic, difficulty, "hybrid_coordinate",
            f"Find the distance between the points ({x1}, {y1}) and ({x2}, {y2}).",
            AnswerShape.SINGLE_VALUE, sp.Integer(distance),
        )

    if topic == "calculus":
        kind = proposal.get("kind")
        if kind not in ("derivative", "definite_integral", "limit", "indefinite_integral"):
            raise ValueError("The proposed calculus kind is not supported.")
        coefficients = _proposal_int_list(proposal, "coefficients", 3, 5, -15, 15)
        if coefficients[-1] == 0:
            raise ValueError("The highest proposed polynomial coefficient must be nonzero.")
        point = _proposal_int(proposal, "point", -5, 5)
        lower = _proposal_int(proposal, "lower", -5, 5)
        upper = _proposal_int(proposal, "upper", -5, 5)
        if lower >= upper:
            raise ValueError("The proposed integral bounds must be increasing.")
        expr = sum(coefficient * x**power for power, coefficient in enumerate(coefficients))
        if kind == "derivative":
            answer = diff(expr, x).subs(x, point)
            prompt = f"If f(x) = {_format_polynomial(expr)}, find f'({point})."
            shape = AnswerShape.SINGLE_VALUE
        elif kind == "definite_integral":
            answer = integrate(expr, (x, lower, upper))
            prompt = (
                f"Evaluate the definite integral of {_format_polynomial(expr)} dx "
                f"from x = {lower} to x = {upper}."
            )
            shape = AnswerShape.SINGLE_VALUE
        elif kind == "indefinite_integral":
            answer = integrate(expr, x)
            prompt = (
                f"Find an antiderivative of {_format_polynomial(expr)} with respect "
                "to x. You may omit the constant of integration."
            )
            shape = AnswerShape.EXPRESSION
        else:
            answer = limit(expr, x, point)
            prompt = f"Find the limit as x approaches {point} of {_format_polynomial(expr)}."
            shape = AnswerShape.SINGLE_VALUE
        if shape == AnswerShape.SINGLE_VALUE:
            answer = sp.nsimplify(answer, rational=True)
        return _hybrid_result(topic, difficulty, "hybrid_calculus", prompt, shape, answer)

    if topic == "linear_algebra":
        eigenvalue1 = _proposal_int(proposal, "eigenvalue1", -20, 20)
        eigenvalue2 = _proposal_int(proposal, "eigenvalue2", -20, 20)
        basis_index = _proposal_int(proposal, "basis_index", 0, len(_UNIMODULAR_P) - 1)
        if eigenvalue1 == eigenvalue2:
            raise ValueError("The proposed eigenvalues must be distinct.")
        P = _UNIMODULAR_P[basis_index]
        matrix = P * Matrix([[eigenvalue1, 0], [0, eigenvalue2]]) * P.inv()
        rows = matrix.tolist()
        matrix_text = "[[{}, {}], [{}, {}]]".format(rows[0][0], rows[0][1], rows[1][0], rows[1][1])
        return _hybrid_result(
            topic, difficulty, "hybrid_linalg",
            f"Find the eigenvalues of the matrix {matrix_text}.",
            AnswerShape.MULTI_VALUE, [sp.Integer(eigenvalue1), sp.Integer(eigenvalue2)],
        )

    if topic == "matrices_determinants":
        operation = proposal.get("operation")
        if operation not in ("add", "subtract", "determinant"):
            raise ValueError("The proposed matrix operation is not supported.")
        matrix_a = _proposal_matrix(proposal, "matrix_a")
        if operation == "determinant":
            prompt = f"Find the determinant of the matrix {matrix_a.tolist()}."
            answer = sp.Integer(matrix_a.det())
            shape = AnswerShape.SINGLE_VALUE
        else:
            matrix_b = _proposal_matrix(proposal, "matrix_b")
            operator = "+" if operation == "add" else "-"
            answer = matrix_a + matrix_b if operation == "add" else matrix_a - matrix_b
            prompt = (
                f"Compute A {operator} B, where A = {matrix_a.tolist()} and "
                f"B = {matrix_b.tolist()}. Enter matrix rows separated by semicolons "
                "and values by commas (for example: 1, 2; 3, 4)."
            )
            shape = AnswerShape.VECTOR_OR_MATRIX
        return _hybrid_result(topic, difficulty, "hybrid_matrix", prompt, shape, answer)

    if topic == "vectors_3d":
        operation = proposal.get("operation")
        if operation not in ("dot", "cross"):
            raise ValueError("The proposed vector operation must be dot or cross.")
        vector_a = _proposal_int_list(proposal, "vector_a", 3, 3, -10, 10)
        vector_b = _proposal_int_list(proposal, "vector_b", 3, 3, -10, 10)
        if operation == "cross":
            answer = Matrix(vector_a).cross(Matrix(vector_b))
            prompt = (
                f"Find a × b for a = {tuple(vector_a)} and b = {tuple(vector_b)}. "
                "Enter the three components separated by commas."
            )
            shape = AnswerShape.VECTOR_OR_MATRIX
        else:
            answer = sp.Integer(sum(a * b for a, b in zip(vector_a, vector_b)))
            prompt = f"Find the dot product of vectors a = {tuple(vector_a)} and b = {tuple(vector_b)}."
            shape = AnswerShape.SINGLE_VALUE
        return _hybrid_result(topic, difficulty, "hybrid_vectors", prompt, shape, answer)

    if topic == "sets_relations":
        size_a = _proposal_int(proposal, "size_a", 2, 50)
        size_b = _proposal_int(proposal, "size_b", 2, 50)
        intersection = _proposal_int(proposal, "intersection", 1, min(size_a, size_b) - 1)
        union = size_a + size_b - intersection
        prompt = (
            f"Set A has {size_a} elements, Set B has {size_b} elements, and "
            f"|A intersect B| = {intersection}. Find |A union B|."
        )
        return _hybrid_result(
            topic, difficulty, "hybrid_sets", prompt,
            AnswerShape.SINGLE_VALUE, sp.Integer(union),
        )

    raise ValueError(f"No hybrid generator is available for topic: {topic}")


def _hybrid_result(topic, difficulty, prefix, prompt, answer_shape, answer, **extra):
    return {
        "id": _rand_id(prefix),
        "topic": topic,
        "difficulty": difficulty,
        "prompt_text": prompt,
        "answer_shape": answer_shape,
        "canonical_answer": answer,
        **extra,
    }


def _proposal_int(proposal: dict, key: str, minimum: int, maximum: int) -> int:
    value = proposal.get(key)
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"The proposed {key} must be an integer between {minimum} and {maximum}.")
    return value


def _proposal_choice(proposal: dict, key: str, choices):
    value = proposal.get(key)
    if type(value) is not int or value not in choices:
        raise ValueError(f"The proposed {key} must be one of {choices}.")
    return value


def _proposal_bool(proposal: dict, key: str) -> bool:
    value = proposal.get(key)
    if type(value) is not bool:
        raise ValueError(f"The proposed {key} must be a boolean.")
    return value


def _proposal_int_list(proposal: dict, key: str, min_length: int, max_length: int, minimum: int, maximum: int):
    values = proposal.get(key)
    if (
        not isinstance(values, list)
        or not min_length <= len(values) <= max_length
        or any(type(value) is not int or not minimum <= value <= maximum for value in values)
    ):
        raise ValueError(
            f"The proposed {key} must contain {min_length}-{max_length} "
            f"integers between {minimum} and {maximum}."
        )
    return values


def _proposal_matrix(proposal: dict, key: str) -> Matrix:
    rows = proposal.get(key)
    if not isinstance(rows, list) or len(rows) != 2:
        raise ValueError(f"The proposed {key} must be a 2x2 integer matrix.")
    if any(
        not isinstance(row, list)
        or len(row) != 2
        or any(type(value) is not int or not -10 <= value <= 10 for value in row)
        for row in rows
    ):
        raise ValueError(f"The proposed {key} must be a 2x2 integer matrix from -10 to 10.")
    return Matrix(rows)


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
    kind = random.choice(["derivative", "definite_integral", "limit", "indefinite_integral"])
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

    elif kind == "indefinite_integral":
        answer = integrate(expr, x)
        prompt_text = (
            f"Find an antiderivative of {_format_polynomial(expr)} with respect to x. "
            "You may omit the constant of integration."
        )
    else:  # limit — polynomials are continuous everywhere, so this is just substitution
        point = random.randint(-3, 3)
        answer = limit(expr, x, point)
        prompt_text = f"Find the limit as x approaches {point} of {_format_polynomial(expr)}."

    answer_shape = AnswerShape.EXPRESSION if kind == "indefinite_integral" else AnswerShape.SINGLE_VALUE
    if answer_shape == AnswerShape.SINGLE_VALUE:
        answer = sp.nsimplify(answer, rational=True)

    return {
        "id": _rand_id("calc"),
        "topic": "calculus",
        "difficulty": difficulty,
        "prompt_text": prompt_text,
        "answer_shape": answer_shape,
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
    """Matrix addition or determinant, chosen to exercise scalar and matrix answers."""
    if random.random() < 0.5:
        A = Matrix([[random.randint(-5, 5) for _ in range(2)] for _ in range(2)])
        B = Matrix([[random.randint(-5, 5) for _ in range(2)] for _ in range(2)])
        operation = random.choice(["+", "-"])
        answer = A + B if operation == "+" else A - B
        prompt_text = (
            f"Compute A {operation} B, where A = {A.tolist()} and B = {B.tolist()}. "
            "Enter matrix rows separated by semicolons and values by commas "
            "(for example: 1, 2; 3, 4)."
        )
        return {
            "id": _rand_id("matop"),
            "topic": "matrices_determinants",
            "difficulty": difficulty,
            "prompt_text": prompt_text,
            "answer_shape": AnswerShape.VECTOR_OR_MATRIX,
            "canonical_answer": answer,
        }

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

    if random.random() < 0.5:
        cross_product = Matrix(v1).cross(Matrix(v2))
        return {
            "id": _rand_id("vec3d"),
            "topic": "vectors_3d",
            "difficulty": difficulty,
            "prompt_text": (
                f"Find a × b for a = {tuple(v1)} and b = {tuple(v2)}. "
                "Enter the three components separated by commas."
            ),
            "answer_shape": AnswerShape.VECTOR_OR_MATRIX,
            "canonical_answer": cross_product,
        }

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
