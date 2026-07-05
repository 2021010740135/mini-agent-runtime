"""计算器工具——执行安全的数学运算"""

import ast
import math

from .base import BaseTool


class CalculatorTool(BaseTool):
    """安全的数学表达式计算器。

    通过 AST 白名单限制，仅允许安全的数学运算。
    支持：四则运算、幂运算、math 模块函数。
    """

    name = "calculator"
    description = "执行数学表达式计算，支持四则运算、幂运算和 math 模块函数（sqrt、sin、cos、log 等）"

    parameters = {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "数学表达式，如 '2 + 3 * 4' 或 'sqrt(16) + pow(2, 3)'",
            },
        },
        "required": ["expression"],
    }

    # 允许的安全 AST 节点类型
    _SAFE_NODES: set[type] = {
        ast.Expression, ast.Constant, ast.UnaryOp, ast.UAdd, ast.USub,
        ast.BinOp, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
        ast.Call, ast.Name, ast.Load,
    }

    # 允许调用的函数 / 常量
    _SAFE_FUNCTIONS: dict = {
        "abs": abs, "round": round, "min": min, "max": max, "pow": pow,
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "log": math.log, "log10": math.log10, "log2": math.log2,
        "exp": math.exp, "floor": math.floor, "ceil": math.ceil,
        "pi": math.pi, "e": math.e,
    }

    async def execute(self, **kwargs) -> str:
        """安全执行数学表达式。

        Args:
            expression: 数学表达式字符串

        Returns:
            计算结果字符串，或错误信息
        """
        expression = kwargs.get("expression", "").strip()
        if not expression:
            return "错误：表达式不能为空"

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError:
            return f"错误：表达式语法无效 '{expression}'"

        if not self._is_safe(tree):
            return f"错误：表达式包含不允许的操作"

        try:
            result = eval(
                compile(tree, "<calculator>", "eval"),
                {"__builtins__": {}},
                self._SAFE_FUNCTIONS,
            )
            return str(result)
        except ZeroDivisionError:
            return "错误：不能除以零"
        except Exception as e:
            return f"计算错误：{e}"

    def _is_safe(self, node: ast.AST) -> bool:
        """递归检查 AST 节点是否都在安全白名单内。"""
        if type(node) not in self._SAFE_NODES:
            return False
        for child in ast.iter_child_nodes(node):
            if not self._is_safe(child):
                return False
        return True