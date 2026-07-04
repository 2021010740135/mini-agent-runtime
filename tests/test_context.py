"""测试 ContextManager"""

from agent.context import ContextManager


def test_context_manager_creation():
    """验证 ContextManager 可被实例化."""
    ctx = ContextManager(max_tokens=4096)
    assert ctx.max_tokens == 4096
