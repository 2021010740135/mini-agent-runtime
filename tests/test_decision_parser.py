"""测试 DecisionEngine"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from agent.decision import Decision, DecisionEngine, ToolCall
from agent.errors import DecisionError, ToolError
from tools.registry import ToolRegistry


# ── 辅助 ──────────────────────────────────

class _FakeTool:
    """模拟工具，不是真正的 BaseTool 但实现了 execute."""
    def __init__(self, name, description="", parameters=None, side_effect=None):
        self.name = name
        self.description = description
        self.parameters = parameters or {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "查询内容"},
            },
            "required": ["query"],
        }
        self.side_effect = side_effect

    def to_openai_schema(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **kwargs):
        if self.side_effect:
            return self.side_effect(**kwargs)
        return f"工具 {self.name} 执行结果"


def _make_mock_completion(content=None, tool_calls=None):
    """构造模拟的 OpenAI Completion 响应."""
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None

    if tool_calls:
        tc_objs = []
        for tc in tool_calls:
            obj = MagicMock()
            obj.id = tc["id"]
            obj.function.name = tc["name"]
            obj.function.arguments = json.dumps(tc["arguments"], ensure_ascii=False)
            tc_objs.append(obj)
        msg.tool_calls = tc_objs

    choice = MagicMock()
    choice.message = msg

    response = MagicMock()
    response.choices = [choice]
    return response


@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register(_FakeTool(name="search", description="搜索"))
    r.register(_FakeTool(name="calculator", description="计算"))
    return r


def _make_engine(registry, completions_side_effect):
    """构造 DecisionEngine，注入模拟 LLMClient."""
    mock_client = MagicMock()
    mock_client.model = "test-model"
    mock_llm = MagicMock()
    mock_llm.model = "test-model"
    mock_llm.client.chat.completions.create.side_effect = completions_side_effect
    return DecisionEngine(llm_client=mock_llm, tool_registry=registry, max_iterations=3)


# ═══════════════════════════════════════
# Decision 数据类
# ═══════════════════════════════════════

class TestDecision:
    def test_is_final_without_tool_calls(self):
        d = Decision(content="最终回复")
        assert d.is_final is True

    def test_is_final_with_tool_calls(self):
        d = Decision(content="我先查一下", tool_calls=[
            ToolCall(id="1", name="search", arguments={"query": "test"})
        ])
        assert d.is_final is False

    def test_default_tool_calls_empty(self):
        d = Decision()
        assert d.tool_calls == []


# ═══════════════════════════════════════
# ToolCall 数据类
# ═══════════════════════════════════════

class TestToolCall:
    def test_tool_call_fields(self):
        tc = ToolCall(id="call_1", name="search", arguments={"query": "天气"})
        assert tc.id == "call_1"
        assert tc.name == "search"
        assert tc.arguments == {"query": "天气"}


# ═══════════════════════════════════════
# DecisionEngine 初始化
# ═══════════════════════════════════════

class TestDecisionEngineInit:
    def test_creation(self, registry):
        mock_llm = MagicMock()
        mock_llm.model = "test"
        engine = DecisionEngine(llm_client=mock_llm, tool_registry=registry)
        assert engine.llm is mock_llm
        assert engine.registry is registry
        assert engine.max_iterations == 5

    def test_custom_max_iterations(self, registry):
        mock_llm = MagicMock()
        mock_llm.model = "test"
        engine = DecisionEngine(
            llm_client=mock_llm, tool_registry=registry, max_iterations=10,
        )
        assert engine.max_iterations == 10


# ═══════════════════════════════════════
# run() —— 核心流程
# ═══════════════════════════════════════

class TestRun:
    @pytest.mark.asyncio
    async def test_no_tools_returns_directly(self, registry):
        """验证无工具调用时直接返回文本."""
        engine = _make_engine(
            registry,
            [_make_mock_completion(content="你好！有什么可以帮你的？")],
        )
        result = await engine.run([{"role": "user", "content": "你好"}])
        assert "你好" in result

    @pytest.mark.asyncio
    async def test_single_tool_call_then_answer(self, registry):
        """验证 1 次工具调用 → 最终回复."""
        engine = _make_engine(registry, [
            _make_mock_completion(  # 第 1 轮：发起工具调用
                content="让我查一下",
                tool_calls=[{"id": "c1", "name": "search", "arguments": {"query": "Python"}}],
            ),
            _make_mock_completion(  # 第 2 轮：最终回复
                content="根据搜索结果，Python 是一种编程语言。",
            ),
        ])
        result = await engine.run([{"role": "user", "content": "什么是 Python？"}])
        assert "Python 是一种编程语言" in result

    @pytest.mark.asyncio
    async def test_multiple_iterations(self, registry):
        """验证多轮工具调用."""
        engine = _make_engine(registry, [
            _make_mock_completion(  # 第 1 轮
                content=None,
                tool_calls=[{"id": "c1", "name": "search", "arguments": {"query": "Python"}}],
            ),
            _make_mock_completion(  # 第 2 轮
                content=None,
                tool_calls=[{"id": "c2", "name": "calculator", "arguments": {"expression": "2+3"}}],
            ),
            _make_mock_completion(  # 第 3 轮：最终
                content="搜索完成，计算结果为 5。",
            ),
        ])
        result = await engine.run([{"role": "user", "content": "搜索 Python 并计算 2+3"}])
        assert "5" in result

    @pytest.mark.asyncio
    async def test_multi_tool_calls_in_one_response(self, registry):
        """验证单轮 LLM 返回 2 个 tool_calls 的情况."""
        engine = _make_engine(registry, [
            _make_mock_completion(
                content=None,
                tool_calls=[
                    {"id": "c1", "name": "search", "arguments": {"query": "Python"}},
                    {"id": "c2", "name": "calculator", "arguments": {"expression": "1+1"}},
                ],
            ),
            _make_mock_completion(content="综合結果：Python 很棒，1+1=2"),
        ])
        result = await engine.run([{"role": "user", "content": "查询并计算"}])
        assert "Python" in result

    @pytest.mark.asyncio
    async def test_llm_call_error(self, registry):
        """验证 LLM 调用失败抛出 DecisionError."""
        mock_llm = MagicMock()
        mock_llm.model = "test"
        mock_llm.client.chat.completions.create.side_effect = Exception("API 超时")
        engine = DecisionEngine(llm_client=mock_llm, tool_registry=registry)

        with pytest.raises(DecisionError, match="API 超时"):
            await engine.run([{"role": "user", "content": "hi"}])

    @pytest.mark.asyncio
    async def test_max_iterations_exceeded(self, registry):
        """验证超过最大迭代次数抛出 DecisionError."""
        # 永远返回 tool_calls，永远不会结束
        completions = [
            _make_mock_completion(
                content=None,
                tool_calls=[{"id": f"c{i}", "name": "search", "arguments": {"query": "loop"}}],
            )
            for i in range(5)
        ]
        engine = _make_engine(registry, completions)
        engine.max_iterations = 2

        with pytest.raises(DecisionError, match="超过最大迭代"):
            await engine.run([{"role": "user", "content": "死循环"}])

    @pytest.mark.asyncio
    async def test_tool_execution_error(self, registry):
        """验证工具执行失败时错误信息返回给 LLM 继续."""
        bad_tool = _FakeTool(
            name="bad_tool",
            side_effect=lambda **kw: ValueError("模拟失败"),
        )
        registry.register(bad_tool)

        engine = _make_engine(registry, [
            _make_mock_completion(
                content=None,
                tool_calls=[{"id": "c1", "name": "bad_tool", "arguments": {}}],
            ),
            _make_mock_completion(content="工具调用失败，我换个方式回答。"),
        ])
        result = await engine.run([{"role": "user", "content": "hi"}])
        assert "换个方式" in result

    @pytest.mark.asyncio
    async def test_tool_not_found(self, registry):
        """验证调用未注册工具返回错误."""
        engine = _make_engine(registry, [
            _make_mock_completion(
                content=None,
                tool_calls=[{"id": "c1", "name": "nonexistent", "arguments": {}}],
            ),
            _make_mock_completion(content="这个工具不存在，我直接回答。"),
        ])
        result = await engine.run([{"role": "user", "content": "hi"}])
        assert "直接回答" in result

    @pytest.mark.asyncio
    async def test_empty_registry_fallback(self, registry):
        """验证无工具时直接用 llm.chat() 返回."""
        empty_registry = ToolRegistry()  # 没有注册任何工具
        mock_llm = MagicMock()
        mock_llm.model = "test"
        mock_llm.chat.return_value = "直接回复"
        engine = DecisionEngine(llm_client=mock_llm, tool_registry=empty_registry)

        result = await engine.run([{"role": "user", "content": "hi"}])
        assert result == "直接回复"
        mock_llm.chat.assert_called_once()