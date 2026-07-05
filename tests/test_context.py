"""测试 ContextManager 模块"""

from unittest.mock import MagicMock, patch

import pytest

from agent.context import ContextManager


def test_context_manager_creation():
    """验证 ContextManager 实例化."""
    ctx = ContextManager(max_tokens=4096, keep_recent=8)
    assert ctx.max_tokens == 4096
    assert ctx.keep_recent == 8
    assert ctx.summary == ""


def test_estimate_tokens():
    """验证 token 估算：约 2 字符 = 1 token."""
    assert ContextManager.estimate_tokens("你好") == 1        # 2 字符
    assert ContextManager.estimate_tokens("hello") == 2      # 5 字符
    assert ContextManager.estimate_tokens("") == 1           # 空字符串返回 1


def test_estimate_tokens_batch():
    """验证批量 token 估算."""
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"},
    ]
    tokens = ContextManager.estimate_tokens_batch(messages)
    assert tokens == ContextManager.estimate_tokens("你好") + \
           ContextManager.estimate_tokens("你好！有什么可以帮你的？")


def test_should_compress_under_limit():
    """验证未超限时不触发压缩."""
    ctx = ContextManager(max_tokens=10000)
    messages = [{"role": "user", "content": "短消息"}]
    assert ctx.should_compress(messages) is False


def test_should_compress_over_limit():
    """验证超限时触发压缩."""
    ctx = ContextManager(max_tokens=10)
    messages = [{"role": "user", "content": "这是一段比较长的测试消息" * 10}]
    assert ctx.should_compress(messages) is True


def test_optimize_no_compression_needed():
    """验证未超限时 optimize 原样返回（加 system prompt）."""
    ctx = ContextManager(max_tokens=10000)
    messages = [{"role": "user", "content": "你好"}]

    result = ctx.optimize("你是 AI 助手", messages)

    assert len(result) == 2
    assert result[0] == {"role": "system", "content": "你是 AI 助手"}
    assert result[1]["content"] == "你好"


def test_optimize_sliding_window_without_llm():
    """验证超限时使用降级截断策略（无 LLM）."""
    ctx = ContextManager(max_tokens=20, keep_recent=2)

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第二轮问题第二轮问题第二轮问题"},
        {"role": "assistant", "content": "第二轮回答第二轮回答第二轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    # system + summary + 最近 2 条
    assert result[0]["role"] == "system"
    assert "历史消息" in result[1]["content"]  # summary
    assert len(result) == 4  # system + summary + 2 recent


def test_optimize_with_llm_summary():
    """验证超限时优先使用 LLM 生成摘要."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "这是一段 LLM 生成的摘要"

    ctx = ContextManager(max_tokens=20, keep_recent=2, llm_client=mock_llm)

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第二轮问题第二轮问题第二轮问题"},
        {"role": "assistant", "content": "第二轮回答第二轮回答第二轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert "LLM 生成的摘要" in result[1]["content"]
    mock_llm.chat.assert_called_once()


def test_optimize_llm_fails_fallback():
    """验证 LLM 摘要失败时降级为截断摘要."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = Exception("LLM 调用失败")

    ctx = ContextManager(max_tokens=10, keep_recent=2, llm_client=mock_llm)

    # 5 轮对话，溢出 3 轮（6 条），走 _truncation_summary 第二个分支
    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第二轮问题第二轮问题第二轮问题"},
        {"role": "assistant", "content": "第二轮回答第二轮回答第二轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert "已省略" in result[1]["content"]  # 降级摘要
    assert ctx.summary != ""


def test_context_clear():
    """验证 clear 清空摘要."""
    ctx = ContextManager(max_tokens=10, keep_recent=2)

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]
    ctx.optimize("SYS", messages)
    assert ctx.summary != ""

    ctx.clear()
    assert ctx.summary == ""


