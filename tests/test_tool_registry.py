"""测试 ToolRegistry"""

from tools.registry import ToolRegistry


def test_registry_empty_on_init():
    """验证注册表初始化时为空."""
    registry = ToolRegistry()
    assert len(registry._tools) == 0
