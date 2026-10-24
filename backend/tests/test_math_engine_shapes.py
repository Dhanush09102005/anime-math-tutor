import json

import sympy as sp

from math_engine.generate import (
    HYBRID_PROPOSAL_INSTRUCTIONS,
    TOPIC_GENERATORS,
    _generate_calculus,
    _generate_matrices_determinants,
    _generate_vectors_3d,
    generate_problem,
    generate_problem_from_proposal,
)
from math_engine.verify import verify_answer
from personas.prompt_builder import format_answer_for_display
from db.session_state import deserialize_active_problem, serialize_active_problem
from schemas import AnswerShape


def test_matrix_answers_are_checked_by_shape_and_value():
    problem = {
        "answer_shape": AnswerShape.VECTOR_OR_MATRIX,
        "canonical_answer": sp.Matrix([[2, -1], [0, 3]]),
    }

    correct = verify_answer(problem, "2, -1; 0, 3")
    partial = verify_answer(problem, "2, -1; 0, 4")
    malformed = verify_answer(problem, "2, nope; 0, 3")

    assert correct["correct"] is True
    assert partial["mistake_type"] == "partial"
    assert malformed["not_serious"] is True
    assert format_answer_for_display(problem["canonical_answer"]) == "2, -1; 0, 3"


def test_vector_answers_preserve_order():
    problem = {
        "answer_shape": AnswerShape.VECTOR_OR_MATRIX,
        "canonical_answer": [sp.Integer(2), sp.Integer(-3), sp.Integer(5)],
    }

    assert verify_answer(problem, "2, -3, 5")["correct"] is True
    assert verify_answer(problem, "5, -3, 2")["correct"] is False


def test_antiderivatives_accept_equivalent_expressions_and_constants():
    problem = {
        "answer_shape": AnswerShape.EXPRESSION,
        "canonical_answer": sp.integrate(3 * sp.Symbol("x") ** 2, sp.Symbol("x")),
    }

    assert verify_answer(problem, "x^3 + C")["correct"] is True
    assert verify_answer(problem, "3*x^2")["correct"] is False
    assert verify_answer(problem, "not math")["not_serious"] is True


def test_matrix_generator_emits_matrix_answer_shape(monkeypatch):
    monkeypatch.setattr("math_engine.generate.random.random", lambda: 0.0)

    problem = _generate_matrices_determinants(2)
    answer = "; ".join(", ".join(str(value) for value in row) for row in problem["canonical_answer"].tolist())

    assert problem["answer_shape"] == AnswerShape.VECTOR_OR_MATRIX
    assert verify_answer(problem, answer)["correct"] is True


def test_vector_generator_emits_vector_answer_shape(monkeypatch):
    monkeypatch.setattr("math_engine.generate.random.random", lambda: 0.0)

    problem = _generate_vectors_3d(2)
    answer = ", ".join(str(value) for value in problem["canonical_answer"])

    assert problem["answer_shape"] == AnswerShape.VECTOR_OR_MATRIX
    assert verify_answer(problem, answer)["correct"] is True
    assert format_answer_for_display(problem["canonical_answer"]) == answer


def test_calculus_generator_can_emit_symbolic_answers(monkeypatch):
    monkeypatch.setattr(
        "math_engine.generate.random.choice",
        lambda choices: "indefinite_integral" if "indefinite_integral" in choices else choices[0],
    )

    problem = _generate_calculus(2)

    assert problem["answer_shape"] == AnswerShape.EXPRESSION
    assert verify_answer(problem, str(problem["canonical_answer"]) + " + C")["correct"] is True


def test_hybrid_problem_uses_sympy_computed_answers():
    linear = generate_problem_from_proposal(
        "linear_equations",
        2,
        {"a": 3, "b": -4, "solution": 5},
    )
    quadratic = generate_problem_from_proposal(
        "quadratic_equations",
        2,
        {"root1": -2, "root2": 4, "leading": 2},
    )

    assert linear["canonical_answer"] == 5
    assert "11" in linear["prompt_text"]
    assert set(quadratic["canonical_answer"]) == {-2, 4}


def test_hybrid_problem_rejects_invalid_model_parameters():
    try:
        generate_problem_from_proposal(
            "linear_equations",
            2,
            {"a": 0, "b": 4, "solution": 3},
        )
    except ValueError as error:
        assert "nonzero" in str(error)
    else:
        raise AssertionError("Invalid AI parameters must not produce a problem.")


def test_hybrid_proposals_cover_all_topics_and_produce_varied_verifiable_problems():
    proposals = {
        "linear_equations": (
            {"a": 3, "b": -4, "solution": 5},
            {"a": -2, "b": 7, "solution": -3},
        ),
        "numbers": (
            {"divisor": 7, "quotient": 5, "remainder": 3},
            {"divisor": 11, "quotient": 8, "remainder": 6},
        ),
        "logarithms": (
            {"base": 2, "exponent": 4},
            {"base": 5, "exponent": 3},
        ),
        "quadratic_equations": (
            {"root1": -2, "root2": 4, "leading": 2},
            {"root1": 3, "root2": 7, "leading": 1},
        ),
        "progressions": (
            {"first_term": 2, "difference": 3, "term_number": 8},
            {"first_term": -5, "difference": 4, "term_number": 12},
        ),
        "binomial_theorem": (
            {"n": 8, "k": 3},
            {"n": 12, "k": 5},
        ),
        "complex_numbers": (
            {"triple_index": 0, "swap": False, "imaginary_sign": "plus"},
            {"triple_index": 4, "swap": True, "imaginary_sign": "minus"},
        ),
        "trigonometry": (
            {"equation_index": 0},
            {"equation_index": 9},
        ),
        "probability": (
            {"red": 3, "blue": 5},
            {"red": 9, "blue": 4},
        ),
        "statistics": (
            {"values": [2, 4, 6, 8]},
            {"values": [-3, 5, 10, 12, 16]},
        ),
        "coordinate_geometry": (
            {"triple_index": 0, "x1": 1, "y1": 2, "x_sign": 1, "y_sign": -1},
            {"triple_index": 4, "x1": -8, "y1": 6, "x_sign": -1, "y_sign": 1},
        ),
        "calculus": (
            {
                "kind": "derivative",
                "coefficients": [1, -2, 3],
                "point": 2,
                "lower": -2,
                "upper": 3,
            },
            {
                "kind": "indefinite_integral",
                "coefficients": [2, 0, 1, -1],
                "point": -1,
                "lower": -3,
                "upper": 4,
            },
        ),
        "linear_algebra": (
            {"eigenvalue1": 2, "eigenvalue2": 5, "basis_index": 0},
            {"eigenvalue1": -4, "eigenvalue2": 7, "basis_index": 2},
        ),
        "matrices_determinants": (
            {
                "operation": "add",
                "matrix_a": [[1, 2], [3, 4]],
                "matrix_b": [[5, 6], [7, 8]],
            },
            {
                "operation": "determinant",
                "matrix_a": [[2, 5], [1, 4]],
                "matrix_b": [[0, 0], [0, 0]],
            },
        ),
        "vectors_3d": (
            {"operation": "dot", "vector_a": [1, 2, 3], "vector_b": [4, 5, 6]},
            {"operation": "cross", "vector_a": [2, -1, 3], "vector_b": [0, 4, 1]},
        ),
        "sets_relations": (
            {"size_a": 12, "size_b": 9, "intersection": 4},
            {"size_a": 25, "size_b": 17, "intersection": 8},
        ),
    }

    assert set(HYBRID_PROPOSAL_INSTRUCTIONS) == set(TOPIC_GENERATORS)
    assert set(proposals) == set(TOPIC_GENERATORS)

    for topic, (first_proposal, second_proposal) in proposals.items():
        first = generate_problem_from_proposal(topic, 3, first_proposal)
        second = generate_problem_from_proposal(topic, 3, second_proposal)
        restored = deserialize_active_problem(serialize_active_problem(first))

        assert first["prompt_text"] != second["prompt_text"], topic
        assert first["answer_shape"] in AnswerShape
        formatted_answer = format_answer_for_display(first["canonical_answer"])
        assert verify_answer(first, formatted_answer)["correct"] is True, topic
        assert verify_answer(restored, formatted_answer)["correct"] is True, topic


def test_generated_active_problems_for_all_topics_are_persistable():
    for topic in TOPIC_GENERATORS:
        for _ in range(3):
            problem = generate_problem(topic, 3)
            serialized = serialize_active_problem(problem)
            json.dumps(serialized)
            restored = deserialize_active_problem(serialized)
            answer = format_answer_for_display(problem["canonical_answer"])

            assert verify_answer(restored, answer)["correct"] is True, topic
