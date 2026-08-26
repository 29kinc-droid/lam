from __future__ import annotations

import ast
import operator
from collections.abc import Callable
from typing import Any

from lam.tools.registry import Tool

_BINARY_OPS: dict[type, Callable[[float, float], float]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY_OPS: dict[type, Callable[[float], float]] = {
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.expr) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        binary_op = _BINARY_OPS[type(node.op)]
        return binary_op(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        unary_op = _UNARY_OPS[type(node.op)]
        return unary_op(_eval(node.operand))
    raise ValueError(f"지원하지 않는 표현식입니다: {ast.dump(node)}")


def calculate(args: dict[str, Any]) -> str:
    expression = str(args["expression"])
    tree = ast.parse(expression, mode="eval")
    result = _eval(tree.body)
    return str(result)


CALCULATOR_TOOL = Tool(
    name="calculator",
    description=(
        "사칙연산·거듭제곱 등 수치 계산이 필요할 때 사용한다. "
        "계산이 필요 없는 일반 질문에는 사용하지 않는다."
    ),
    fn=calculate,
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "계산할 산술 표현식 (예: '3 * (4 + 5)')",
            }
        },
        "required": ["expression"],
    },
)
