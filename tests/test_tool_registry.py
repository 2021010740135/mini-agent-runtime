"""测试 ToolRegistry 和 BaseTool"""

import pytest

from tools.base import BaseTool
from tools.registry import ToolRegistry
from agent.errors import ToolError


# ═══════════════════════════════════════
# 辅助：最小化的假工具
# ═══════════════════════════════════════

class _FakeTool(BaseTool):
    name = "fake_tool"
    description = "一个测试用的假工具"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "查询内容"},
        },
        "required": ["query"],
    }

    async def execute(self, **kwargs) -> str:
        return f"fake result: {kwargs}"


class _AnotherTool(BaseTool):
    name = "another_tool"
    description = "另一个测试工具"

    async def execute(self, **kwargs) -> str:
        return "another"


# ═══════════════════════════════════════
# 初始化
# ═══════════════════════════════════════

def test_registry_empty_on_init():
    """验证注册表初始化时为空。"""
    registry = ToolRegistry()
    assert len(registry._tools) == 0
    assert registry.tool_count == 0
    assert registry.list_tools() == []


# ═══════════════════════════════════════
# 注册
# ═══════════════════════════════════════

def test_register_tool():
    """验证注册一个工具。"""
    registry = ToolRegistry()
    tool = _FakeTool()
    registry.register(tool)
    assert registry.tool_count == 1
    assert "fake_tool" in registry
    assert registry.get("fake_tool") is tool


def test_register_multiple_tools():
    """验证注册多个工具。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    registry.register(_AnotherTool())
    assert registry.tool_count == 2
    assert set(registry.list_tools()) == {"fake_tool", "another_tool"}


def test_register_duplicate_raises():
    """验证重复注册抛出 ToolError。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    with pytest.raises(ToolError, match="已注册"):
        registry.register(_FakeTool())


def test_register_nameless_tool_raises():
    """验证 name 为空时注册抛出 ToolError。"""
    registry = ToolRegistry()

    class _NamelessTool(BaseTool):
        name = ""
        description = "无名工具"
        async def execute(self, **kwargs) -> str:
            return ""

    with pytest.raises(ToolError, match="不能为空"):
        registry.register(_NamelessTool())


# ═══════════════════════════════════════
# 注销
# ═══════════════════════════════════════

def test_unregister_tool():
    """验证注销已注册工具。"""
    registry = ToolRegistry()
    tool = _FakeTool()
    registry.register(tool)
    registry.unregister("fake_tool")
    assert registry.tool_count == 0
    assert "fake_tool" not in registry


def test_unregister_nonexistent_raises():
    """验证注销未注册的工具抛出 ToolError。"""
    registry = ToolRegistry()
    with pytest.raises(ToolError, match="未注册"):
        registry.unregister("nonexistent")


# ═══════════════════════════════════════
# 获取
# ═══════════════════════════════════════

def test_get_existing_tool():
    """验证获取已注册工具。"""
    registry = ToolRegistry()
    tool = _FakeTool()
    registry.register(tool)
    assert registry.get("fake_tool").name == "fake_tool"


def test_get_nonexistent_raises():
    """验证获取未注册的工具抛出 ToolError。"""
    registry = ToolRegistry()
    with pytest.raises(ToolError, match="未注册"):
        registry.get("nonexistent")


# ═══════════════════════════════════════
# list_tools
# ═══════════════════════════════════════

def test_list_tools_empty():
    """验证空注册表 list_tools 返回空列表。"""
    registry = ToolRegistry()
    assert registry.list_tools() == []


def test_list_tools_order():
    """验证 list_tools 保持注册先后顺序。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    registry.register(_AnotherTool())
    assert registry.list_tools() == ["fake_tool", "another_tool"]


def test_list_tools_after_unregister():
    """验证注销后 list_tools 不再包含被注销的工具。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    registry.register(_AnotherTool())
    registry.unregister("fake_tool")
    assert registry.list_tools() == ["another_tool"]


# ═══════════════════════════════════════
# get_tools_schema
# ═══════════════════════════════════════

def test_get_tools_schema_empty():
    """验证空注册表返回空列表。"""
    registry = ToolRegistry()
    assert registry.get_tools_schema() == []


def test_get_tools_schema_single():
    """验证单个工具的 schema 格式正确。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())

    schema = registry.get_tools_schema()
    assert len(schema) == 1
    assert schema[0]["type"] == "function"
    func = schema[0]["function"]
    assert func["name"] == "fake_tool"
    assert func["description"] == "一个测试用的假工具"
    assert "query" in func["parameters"]["properties"]
    assert func["parameters"]["required"] == ["query"]


def test_get_tools_schema_multiple():
    """验证多个工具的 schema 顺序与注册一致。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    registry.register(_AnotherTool())

    schema = registry.get_tools_schema()
    assert len(schema) == 2
    names = [s["function"]["name"] for s in schema]
    assert names == ["fake_tool", "another_tool"]


# ═══════════════════════════════════════
# BaseTool.to_openai_schema
# ═══════════════════════════════════════

def test_to_openai_schema_without_parameters():
    """验证工具无 parameters 时生成默认空 schema。"""
    tool = _AnotherTool()

    schema = tool.to_openai_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "another_tool"
    assert schema["function"]["parameters"] == {
        "type": "object",
        "properties": {},
        "required": [],
    }


def test_to_openai_schema_nameless_raises():
    """验证 name 为空时抛出 ValueError。"""
    class _NamelessTool(BaseTool):
        name = ""
        description = "无名"
        async def execute(self, **kwargs) -> str:
            return ""

    with pytest.raises(ValueError, match="不能为空"):
        _NamelessTool().to_openai_schema()


# ═══════════════════════════════════════
# 魔术方法
# ═══════════════════════════════════════

def test_len_magic():
    """验证 len(registry)。"""
    registry = ToolRegistry()
    assert len(registry) == 0
    registry.register(_FakeTool())
    assert len(registry) == 1


def test_contains_magic():
    """验证 in 运算符。"""
    registry = ToolRegistry()
    assert "fake_tool" not in registry
    registry.register(_FakeTool())
    assert "fake_tool" in registry


def test_repr_empty():
    """验证空注册表的 __repr__。"""
    registry = ToolRegistry()
    assert "(空)" in repr(registry)


def test_repr_with_tools():
    """验证有工具时的 __repr__。"""
    registry = ToolRegistry()
    registry.register(_FakeTool())
    assert "fake_tool" in repr(registry)