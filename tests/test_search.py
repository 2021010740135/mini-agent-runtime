"""测试 MockSearch 工具"""

import pytest

from tools.mock_search import MockSearchTool


@pytest.fixture
def tool():
    return MockSearchTool()


# ── 基本搜索 ──

@pytest.mark.asyncio
async def test_match_exact_keyword(tool):
    """验证精确关键词匹配."""
    result = await tool.execute(query="python")
    assert "Python 是一种解释型" in result


@pytest.mark.asyncio
async def test_match_partial_keyword(tool):
    """验证查询中包含关键词即可匹配."""
    result = await tool.execute(query="Python 异步编程相关")
    # "python" 先匹配 → 返回 python 的结果
    assert "Python 是一种解释型" in result


@pytest.mark.asyncio
async def test_case_insensitive_match(tool):
    """验证大小写不敏感匹配."""
    result = await tool.execute(query="AGENT")
    assert "AI Agent 是能够自主感知环境" in result


@pytest.mark.asyncio
async def test_no_match(tool):
    """验证无匹配关键词时返回提示."""
    result = await tool.execute(query="量子力学")
    assert "未找到" in result
    assert "可用的预设关键词" in result


# ── 错误处理 ──

@pytest.mark.asyncio
async def test_empty_query(tool):
    """验证空关键词返回错误."""
    result = await tool.execute(query="")
    assert "不能为空" in result


# ── schema ──

def test_to_openai_schema(tool):
    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "search"
    assert "query" in schema["function"]["parameters"]["properties"]
    assert schema["function"]["parameters"]["required"] == ["query"]