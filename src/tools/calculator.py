import ast
import math
import operator


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}

_FUNCTIONS = {
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "log": math.log,
    "ln": math.log,
    "exp": math.exp,
}

_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value

    if isinstance(node, ast.Name) and node.id in _CONSTANTS:
        return _CONSTANTS[node.id]

    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 1000:
            raise ValueError("指数绝对值不能超过 1000。")
        return _BINARY_OPERATORS[type(node.op)](left, right)

    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_evaluate(node.operand))

    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        function = _FUNCTIONS.get(node.func.id)
        if function is None or node.keywords:
            raise ValueError("表达式包含不允许的函数调用。")
        arguments = [_evaluate(argument) for argument in node.args]
        return function(*arguments)

    raise ValueError("表达式包含不允许的语法。")


def calculate(expression: str) -> float:
    """Safely calculate a mathematical expression from the allowed subset."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError("表达式不能为空。")
    if len(expression) > 200:
        raise ValueError("表达式过长。")

    try:
        tree = ast.parse(expression, mode="eval")
        result = float(_evaluate(tree))
    except SyntaxError as exc:
        raise ValueError("表达式语法无效。") from exc
    except (ArithmeticError, OverflowError, TypeError) as exc:
        raise ValueError(f"计算失败：{exc}") from exc

    if not math.isfinite(result):
        raise ValueError("计算结果不是有限数值。")

    return result
