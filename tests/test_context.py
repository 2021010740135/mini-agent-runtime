"""测试 ContextManager 模块"""

from unittest.mock import MagicMock

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


# ═══════════════════════════════════════
# chunk_and_summarize（场景 1：首轮长输入）
# ═══════════════════════════════════════

def test_chunk_and_summarize_below_limit():
    """验证文本未超过 chunk_size 时原样返回，不调 LLM."""
    mock_llm = MagicMock()
    text = "短文本"

    result = ContextManager.chunk_and_summarize(text, mock_llm, chunk_size=100)

    assert result == "短文本"
    mock_llm.chat.assert_not_called()


def test_chunk_and_summarize_multiple_chunks():
    """验证多块文本：逐块摘要 → 合并为总摘要."""
    mock_llm = MagicMock()
    # 2 块摘要 + 1 合并 = 3 次 LLM 调用
    mock_llm.chat.side_effect = [
        "块1核心要点",
        "块2核心要点",
        "块1+块2合并摘要",
    ]

    text = "A" * 1500  # chunk_size=1000 → 2 块

    result = ContextManager.chunk_and_summarize(text, mock_llm, chunk_size=1000)

    assert result == "块1+块2合并摘要"
    # 3 次 LLM 调用：2 块摘要 + 1 合并
    assert mock_llm.chat.call_count == 3


def test_chunk_and_summarize_below_limit_shortcut():
    """验证文本未超过 chunk_size 时直接返回原文，不调 LLM."""
    mock_llm = MagicMock()

    text = "A" * 500  # 500 < chunk_size=1000

    result = ContextManager.chunk_and_summarize(text, mock_llm, chunk_size=1000)

    # 未超限 → 不调 LLM，直接返回原文
    assert result == text
    mock_llm.chat.assert_not_called()


def test_chunk_and_summarize_chunk_failure_graceful():
    """验证某块摘要失败时使用截断，不影响后续."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = [
        Exception("块1失败"),
        "块2摘要",
        "合并摘要（块1截断+块2）",
    ]

    text = "A" * 1500  # chunk_size=1000 → 2 块

    result = ContextManager.chunk_and_summarize(text, mock_llm, chunk_size=1000)

    # 即使块1失败，整体流程完成
    assert "合并摘要（块1截断+块2）" == result


# ═══════════════════════════════════════
# optimize（场景 2：多轮对话溢出）
# ═══════════════════════════════════════

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
    ctx = ContextManager(max_tokens=10, keep_recent=2)

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第二轮问题第二轮问题第二轮问题"},
        {"role": "assistant", "content": "第二轮回答第二轮回答第二轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert result[0]["role"] == "system"
    assert "历史消息" in result[1]["content"]
    assert len(result) == 4  # system + summary + 2 recent


def test_optimize_with_llm_summary():
    """验证超限时 LLM 生成摘要（首次压缩，无需合并）."""
    mock_llm = MagicMock()
    mock_llm.chat.return_value = "这是一段 LLM 生成的摘要"

    ctx = ContextManager(max_tokens=10, keep_recent=2, llm_client=mock_llm)

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
    # 只调用了 _summarize_batch，_merge_summaries 因 existing 为空直接返回
    mock_llm.chat.assert_called_once()


def test_optimize_incremental_summary():
    """验证增量压缩：第二次 optimize 合并已有摘要和新摘要.

    已有摘要 "旧摘要A" + 新溢出摘要 "摘要B" → LLM 合并 → "A+B合并摘要"
    """
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = [
        "新溢出摘要B",           # _summarize_batch
        "已有A + 新B合并摘要",    # _merge_summaries
    ]

    ctx = ContextManager(max_tokens=10, keep_recent=2, llm_client=mock_llm)
    ctx._summary = "这是已有的旧摘要A"  # 模拟之前已经压缩过

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert "已有A + 新B合并摘要" in result[1]["content"]
    assert mock_llm.chat.call_count == 2  # _summarize_batch + _merge_summaries


def test_optimize_llm_fails_fallback():
    """验证 LLM 摘要失败时降级为截断摘要."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = Exception("LLM 调用失败")

    ctx = ContextManager(max_tokens=10, keep_recent=2, llm_client=mock_llm)

    # 6 条消息 → 溢出 4 条，LLM 失败 → 降级为截断摘要
    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第二轮问题第二轮问题第二轮问题"},
        {"role": "assistant", "content": "第二轮回答第二轮回答第二轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert "已省略" in result[1]["content"]
    assert ctx.summary != ""


def test_optimize_llm_fails_preserves_existing_summary():
    """验证 LLM 失败但已有摘要时，保留已有摘要不丢失."""
    mock_llm = MagicMock()
    mock_llm.chat.side_effect = Exception("LLM 调用失败")

    ctx = ContextManager(max_tokens=10, keep_recent=2, llm_client=mock_llm)
    ctx._summary = "之前的对话摘要——不应丢失"

    messages = [
        {"role": "user", "content": "第一轮问题第一轮问题第一轮问题"},
        {"role": "assistant", "content": "第一轮回答第一轮回答第一轮回答"},
        {"role": "user", "content": "第三轮"},
        {"role": "assistant", "content": "第三轮回答"},
    ]

    result = ctx.optimize("SYSTEM", messages)

    assert "之前的对话摘要——不应丢失" in result[1]["content"]


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
