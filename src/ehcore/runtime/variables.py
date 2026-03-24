"""
Global variable ve parameter binding yardimcilari.
"""

from __future__ import annotations

import ast
import math
import re
from typing import Any


DIRECT_VAR_PATTERN = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
TEMPLATE_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

_ALLOWED_FUNCTIONS = {
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "int": int,
    "float": float,
    "bool": bool,
    "str": str,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "exp": math.exp,
    "floor": math.floor,
    "ceil": math.ceil,
    "pi": math.pi,
    "e": math.e,
}

_ALLOWED_NODES = (
    ast.Expression,
    ast.Constant,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.Name,
    ast.Load,
    ast.Call,
    ast.List,
    ast.Tuple,
    ast.Dict,
    ast.Subscript,
    ast.Slice,
    ast.Index,
    ast.And,
    ast.Or,
    ast.Not,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.Mod,
    ast.Pow,
    ast.USub,
    ast.UAdd,
    ast.Eq,
    ast.NotEq,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
)


class VariableResolutionError(ValueError):
    """Config icindeki variable veya expression cozumleme hatasi."""


def resolve_config(config: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    return {
        key: resolve_value(value, variables)
        for key, value in config.items()
    }


def resolve_value(value: Any, variables: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: resolve_value(item, variables) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_value(item, variables) for item in value]
    if isinstance(value, tuple):
        return tuple(resolve_value(item, variables) for item in value)
    if not isinstance(value, str):
        return value

    direct_match = DIRECT_VAR_PATTERN.fullmatch(value.strip())
    if direct_match:
        return _lookup_variable(direct_match.group(1), variables)

    if value.startswith("="):
        return _evaluate_expression(value[1:].strip(), variables)

    if "${" in value:
        return TEMPLATE_VAR_PATTERN.sub(
            lambda match: str(_lookup_variable(match.group(1), variables)),
            value,
        )

    return value


def validate_variable_usage(config: dict[str, Any], variables: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, value in config.items():
        try:
            _ = resolve_value(value, variables)
        except VariableResolutionError as exc:
            errors.append(f"{key}: {exc}")
    return errors


def _lookup_variable(name: str, variables: dict[str, Any]) -> Any:
    if name not in variables:
        raise VariableResolutionError(f"Tanimsiz degisken: {name}")
    return variables[name]


def _evaluate_expression(expression: str, variables: dict[str, Any]) -> Any:
    if not expression:
        raise VariableResolutionError("Bos ifade kullanilamaz")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise VariableResolutionError(f"Gecersiz ifade: {expression}") from exc

    _validate_ast(tree, variables)

    scope = dict(_ALLOWED_FUNCTIONS)
    scope.update(variables)
    try:
        return eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, scope)
    except Exception as exc:
        raise VariableResolutionError(f"Ifade cozumlenemedi: {expression}") from exc


def _validate_ast(tree: ast.AST, variables: dict[str, Any]) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise VariableResolutionError("Desteklenmeyen ifade yapisi")
        if isinstance(node, ast.Name):
            if node.id not in variables and node.id not in _ALLOWED_FUNCTIONS:
                raise VariableResolutionError(f"Tanimsiz degisken: {node.id}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in _ALLOWED_FUNCTIONS:
                raise VariableResolutionError("Yalnizca izinli fonksiyonlar cagrilabilir")
