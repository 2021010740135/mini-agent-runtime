"""测试 Calculator 工具"""

import pytest

from tools.calculator import CalculatorTool


@pytest.fixture
def tool():
    return CalculatorTool()


# ── 基本四则运算 ──

@pytest.mark.asyncio
async def test_basic_addition(tool):
    result = await tool.execute(expression="2 + 3")
    assert result == "5"


@pytest.mark.asyncio
async def test_basic_subtraction(tool):
    result = await tool.execute(expression="10 - 4")
    assert result == "6"


@pytest.mark.asyncio
async def test_basic_multiplication(tool):
    result = await tool.execute(expression="3 * 7")
    assert result == "21"


@pytest.mark.asyncio
async def test_basic_division(tool):
    result = await tool.execute(expression="8 / 2")
    assert result == "4.0"


@pytest.mark.asyncio
async def test_power(tool):
    result = await tool.execute(expression="2 ** 10")
    assert result == "1024"


@pytest.mark.asyncio
async def test_complex_expression(tool):
    result = await tool.execute(expression="(3 + 5) * 2 - 4 / 2")
    assert result == "14.0"


# ── math 模块函数 ──

@pytest.mark.asyncio
async def test_sqrt(tool):
    result = await tool.execute(expression="sqrt(16)")
    assert result == "4.0"


@pytest.mark.asyncio
async def test_sin_cos(tool):
    result = await tool.execute(expression="sin(pi / 2)")
    assert result == "1.0"


@pytest.mark.asyncio
async def test_log(tool):
    result = await tool.execute(expression="log(e)")
    assert result == "1.0"


@pytest.mark.asyncio
async def test_ceil_floor(tool):
    result = await tool.execute(expression="ceil(3.14)")
    assert result == "4"


@pytest.mark.asyncio
async def test_abs(tool):
    result = await tool.execute(expression="abs(-5)")
    assert result == "5"


# ── 错误处理 ──

@pytest.mark.asyncio
async def test_empty_expression(tool):
    result = await tool.execute(expression="")
    assert "不能为空" in result


@pytest.mark.asyncio
async def test_zero_division(tool):
    result = await tool.execute(expression="1 / 0")
    assert "不能除以零" in result


@pytest.mark.asyncio
async def test_invalid_syntax(tool):
    result = await tool.execute(expression="2 + +")
    assert "语法无效" in result


@pytest.mark.asyncio
async def test_blocked_import(tool):
    """验证 __import__ 等危险操作被阻断."""
    result = await tool.execute(expression="__import__('os')")
    assert "错误" in result


# ── schema ──

def test_to_openai_schema(tool):
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "calculator"
    assert "expression" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["expression"]