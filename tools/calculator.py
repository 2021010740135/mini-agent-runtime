"""计算器工具——执行基本的数学运算"""

from .base import BaseTool


class CalculatorTool(BaseTool):
    """基本的四则运算计算器."""

    name = "calculator"
    description = "执行数学表达式计算"
