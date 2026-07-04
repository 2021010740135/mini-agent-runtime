"""测试 Calculator 工具"""

import pytest
from tools.calculator import CalculatorTool


@pytest.mark.xfail(reason="CalculatorTool.execute() 尚未实现")
def test_calculator_tool_exists():
    """验证 CalculatorTool 可被实例化."""
    tool = CalculatorTool()
    assert tool.name == "calculator"
