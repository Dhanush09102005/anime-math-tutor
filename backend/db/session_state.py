"""JSON-safe serialization for resumable session state."""

import sympy as sp
from sympy.matrices.matrixbase import MatrixBase

from schemas import AnswerShape


_EXPRESSION_FUNCTIONS = {
    "Add": sp.Add,
    "Mul": sp.Mul,
    "Pow": sp.Pow,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
}


def _encode_math_value(value):
    if isinstance(value, bool) or value is None or isinstance(value, (str, int, float)):
        return value
    if isinstance(value, MatrixBase):
        return {
            "__kind__": "matrix",
            "rows": value.rows,
            "columns": value.cols,
            "values": [[_encode_math_value(cell) for cell in row] for row in value.tolist()],
        }
    if isinstance(value, sp.Integer):
        return {"__kind__": "integer", "value": str(value)}
    if isinstance(value, sp.Rational):
        return {
            "__kind__": "rational",
            "numerator": str(value.p),
            "denominator": str(value.q),
        }
    if isinstance(value, sp.Float):
        return {"__kind__": "float", "value": str(value)}
    if value is sp.pi:
        return {"__kind__": "pi"}
    if isinstance(value, sp.Symbol):
        return {"__kind__": "symbol", "name": value.name}
    if isinstance(value, sp.Basic):
        function_name = value.func.__name__
        if function_name not in _EXPRESSION_FUNCTIONS:
            raise TypeError(f"Unsupported symbolic value for session persistence: {function_name}")
        return {
            "__kind__": "expression",
            "function": function_name,
            "arguments": [_encode_math_value(argument) for argument in value.args],
        }
    if isinstance(value, (list, tuple)):
        return [_encode_math_value(item) for item in value]
    raise TypeError(f"Unsupported session value for persistence: {type(value).__name__}")


def _decode_math_value(value):
    if isinstance(value, list):
        return [_decode_math_value(item) for item in value]
    if not isinstance(value, dict) or "__kind__" not in value:
        return value

    kind = value["__kind__"]
    if kind == "integer":
        return sp.Integer(value["value"])
    if kind == "rational":
        return sp.Rational(value["numerator"], value["denominator"])
    if kind == "float":
        return sp.Float(value["value"])
    if kind == "pi":
        return sp.pi
    if kind == "symbol":
        return sp.Symbol(value["name"])
    if kind == "matrix":
        rows = value["values"]
        if (
            not isinstance(rows, list)
            or len(rows) != value["rows"]
            or any(not isinstance(row, list) or len(row) != value["columns"] for row in rows)
        ):
            raise ValueError("Stored matrix dimensions do not match its values.")
        return sp.Matrix([[_decode_math_value(cell) for cell in row] for row in rows])
    if kind == "expression":
        function = _EXPRESSION_FUNCTIONS.get(value["function"])
        if function is None:
            raise ValueError(f"Unsupported stored symbolic function: {value['function']}")
        return function(*(_decode_math_value(argument) for argument in value["arguments"]))
    raise ValueError(f"Unsupported stored math value kind: {kind}")


def serialize_active_problem(problem: dict | None) -> dict | None:
    if problem is None:
        return None
    return {
        "id": problem["id"],
        "topic": problem["topic"],
        "difficulty": problem["difficulty"],
        "prompt_text": problem["prompt_text"],
        "generation_mode": problem.get("generation_mode", "procedural"),
        "answer_shape": problem["answer_shape"].value
        if isinstance(problem["answer_shape"], AnswerShape)
        else problem["answer_shape"],
        "canonical_answer": _encode_math_value(problem["canonical_answer"]),
    }


def deserialize_active_problem(problem: dict | None) -> dict | None:
    if problem is None:
        return None
    return {
        **problem,
        "generation_mode": problem.get("generation_mode", "procedural"),
        "answer_shape": AnswerShape(problem["answer_shape"]),
        "canonical_answer": _decode_math_value(problem["canonical_answer"]),
    }


def serialize_conversation_history(history: list[dict]) -> list[dict]:
    if not isinstance(history, list):
        raise TypeError("Conversation history must be a list.")
    serialized = []
    for message in history:
        if (
            not isinstance(message, dict)
            or message.get("role") not in ("user", "assistant")
            or not isinstance(message.get("content"), str)
        ):
            raise ValueError("Conversation history contains an invalid message.")
        serialized.append({"role": message["role"], "content": message["content"]})
    return serialized
