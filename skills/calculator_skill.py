"""Calculator Skill."""
from __future__ import annotations

import ast
import math
import operator
from typing import Any

from skills.base_skill import BaseSkill, skill_registry


OPERATORS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}

FUNCTIONS = {
    "abs": abs, "round": round, "min": min, "max": max, "sum": sum,
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "log": math.log, "log10": math.log10, "exp": math.exp,
    "pi": math.pi, "e": math.e, "pow": pow,
}


def _safe_eval(node):
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body)
    elif isinstance(node, ast.Constant):
        return node.value
    elif isinstance(node, ast.BinOp):
        op = OPERATORS.get(type(node.op))
        if not op:
            raise ValueError("Desteklenmeyen operator")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        op = OPERATORS.get(type(node.op))
        if not op:
            raise ValueError("Desteklenmeyen unary")
        return op(_safe_eval(node.operand))
    elif isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Basit fonksiyonlar")
        func_name = node.func.id
        if func_name not in FUNCTIONS:
            raise ValueError(f"Desteklenmeyen: {func_name}")
        args = [_safe_eval(arg) for arg in node.args]
        return FUNCTIONS[func_name](*args)
    elif isinstance(node, ast.Name):
        if node.id in FUNCTIONS:
            return FUNCTIONS[node.id]
        raise ValueError(f"Bilinmeyen: {node.id}")
    else:
        raise ValueError("Desteklenmeyen ifade")


class CalculatorSkill(BaseSkill):
    name = "calculator"
    description = "Matematik hesaplar"

    async def execute(self, expression: str = "", **kwargs) -> dict[str, Any]:
        if not expression:
            return {"error": "Ifade bos"}
        try:
            expr = expression.strip().replace("^", "**").replace(",", "")
            tree = ast.parse(expr, mode="eval")
            result = _safe_eval(tree)
            return {"expression": expression, "result": result, "formatted": f"{result}"}
        except Exception as e:
            return {"error": f"Hata: {str(e)}"}


skill_registry.register(CalculatorSkill())
